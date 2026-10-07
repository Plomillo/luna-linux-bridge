#!/usr/bin/env python3
"""Owner-provisioned, loopback-only mTLS telemetry gateway.

No screenshots, sudo, arbitrary remote commands, project file retrieval or
public binding. A separately authenticated owner-managed tunnel is required
for any off-host client. Never self-certifies or installs its own service.
"""
from __future__ import annotations
import argparse
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import socket
import socketserver
import ssl
import stat
import sys
import threading
from urllib.parse import urlsplit, parse_qs

import lrb_core as base
import live_link

SCHEMA="LRB_MTLS_READONLY_GATEWAY/0.3"
MAX_JSON_BYTES=32768
MAX_CLIENTS=3
HASH=re.compile(r"^[a-f0-9]{64}$")


def guarded_file(path,owner=None,private=False):
    p=Path(path)
    if not p.is_absolute() or p.is_symlink() or not p.is_file():
        raise RuntimeError("MTLS_CONFIG_FILE_PATH_UNSAFE")
    metadata=p.stat()
    if owner is not None and metadata.st_uid != owner:
        raise RuntimeError("MTLS_KEY_OR_POLICY_OWNERSHIP_INVALID")
    if metadata.st_mode & 0o022 or (private and metadata.st_mode & 0o077):
        raise RuntimeError("MTLS_FILE_PERMISSIONS_UNSAFE")
    if metadata.st_size > 32768:
        raise RuntimeError("MTLS_CONFIG_FILE_TOO_LARGE")
    return p


def read_config(path, enforce_root=True):
    p=guarded_file(path,owner=0 if enforce_root else None)
    if enforce_root:
        for ancestor in p.parents:
            if ancestor == Path("/"):break
            info=ancestor.lstat()
            if stat.S_ISLNK(info.st_mode) or info.st_uid!=0 or info.st_mode & 0o022:
                raise RuntimeError("MTLS_CONFIG_PARENT_TRUST_FAILURE")
    try:
        data=json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError("MTLS_CONFIG_INVALID") from exc
    if data.get("schema")!=SCHEMA or set(data)!={
        "schema","server_cert","server_key","client_ca","client_cert_sha256",
        "server_cert_sha256","client_ca_sha256"}:
        raise RuntimeError("MTLS_CONFIG_SCHEMA_OR_KEYS_INVALID")
    for key in ("client_cert_sha256","server_cert_sha256","client_ca_sha256"):
        if not isinstance(data[key],str) or not HASH.fullmatch(data[key]):
            raise RuntimeError("MTLS_KEY_PIN_INVALID")
    if data["server_cert_sha256"]==data["client_ca_sha256"]:
        raise RuntimeError("MTLS_SERVER_AND_CLIENT_AUTH_TRUST_COLLISION")
    for field in ("server_cert","server_key","client_ca"):
        pfile=guarded_file(data[field],owner=os.getuid() if field=="server_key" else
                           (0 if enforce_root else None),private=field=="server_key")
        if field!="server_key":
            h=hashlib.sha256(pfile.read_bytes()).hexdigest()
            if h!=data[field+"_sha256"]:
                raise RuntimeError("MTLS_AUTHENTICATION_PIN_MISMATCH_"+field)
    return data


class Handler(BaseHTTPRequestHandler):
    protocol_version="HTTP/1.0"
    server_version="LOUKSNA-Readonly-mTLS/0.3"

    def log_message(self,fmt,*args):
        # Avoid logging arbitrary hostile URI text and client certificates.
        return

    def send_json(self,body,code=200):
        raw=base.canonical(body)
        if len(raw)>MAX_JSON_BYTES:
            raw=base.canonical({"schema":SCHEMA,"status":"HOLD_RESPONSE_TOO_LARGE",
                                "sha256":base.digest(body),"certified":False})
            code=503
        self.send_response(code)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Content-Length",str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.headers.get("Content-Length") or self.headers.get("Transfer-Encoding"):
            self.send_json({"status":"HOLD_REQUEST_BODY_DENIED"},400)
            return
        parts=urlsplit(self.path)
        if parts.fragment or len(self.path)>120:
            self.send_json({"status":"HOLD_PATH_BOUNDARY"},400)
            return
        if parts.path=="/v1/status" and not parts.query:
            self.send_json(self.server.bridge.dispatch({"op":"status"}))
            return
        if parts.path=="/v1/observe" and not parts.query:
            self.send_json(self.server.bridge.dispatch({"op":"observe"}))
            return
        if parts.path=="/v1/watch":
            query=parse_qs(parts.query,keep_blank_values=True)
            if set(query)!={"frames","interval_sec"} or any(len(v)!=1 for v in query.values()):
                self.send_json({"status":"HOLD_WATCH_QUERY"},400)
                return
            try:
                req={"op":"watch","frames":int(query["frames"][0]),
                     "interval_sec":int(query["interval_sec"][0])}
                if not(1<=req["frames"]<=live_link.MAX_FRAMES
                       and 1<=req["interval_sec"]<=live_link.MAX_INTERVAL_SEC):
                    raise ValueError("watch limit")
                generator=self.server.bridge.watch(req)
            except Exception:
                self.send_json({"status":"HOLD_WATCH_BUDGET"},400)
                return
            self.send_response(200)
            self.send_header("Content-Type","text/event-stream")
            self.send_header("Cache-Control","no-store")
            self.send_header("Connection","close")
            self.end_headers()
            try:
                for message in generator:
                    data=base.canonical(message)
                    if len(data)>MAX_JSON_BYTES:
                        break
                    self.wfile.write(b"data: "+data+b"\n\n")
                    self.wfile.flush()
            except (BrokenPipeError,ConnectionResetError):
                pass
            return
        self.send_json({"status":"HOLD_ROUTE_NOT_REGISTERED"},404)

    def do_POST(self):
        self.send_json({"status":"HOLD_REMOTE_MUTATION_NOT_EXPOSED"},405)

    def do_PUT(self):
        self.send_json({"status":"HOLD_REMOTE_MUTATION_NOT_EXPOSED"},405)

    def do_DELETE(self):
        self.send_json({"status":"HOLD_REMOTE_MUTATION_NOT_EXPOSED"},405)


class Server(socketserver.ThreadingMixIn,HTTPServer):
    daemon_threads=True
    request_queue_size=3
    allow_reuse_address=False

    def __init__(self,bridge,config,port,testing=False):
        if type(port) is not int or (not testing and not 1024<=port<=65535):
            raise RuntimeError("LOOPBACK_PORT_INVALID")
        self.bridge=bridge
        self.client_fingerprint=config["client_cert_sha256"]
        self.slots=threading.BoundedSemaphore(MAX_CLIENTS)
        super().__init__(("127.0.0.1",port),Handler,bind_and_activate=False)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version=ssl.TLSVersion.TLSv1_3
        context.maximum_version=ssl.TLSVersion.TLSv1_3
        context.verify_mode=ssl.CERT_REQUIRED
        context.load_cert_chain(config["server_cert"],config["server_key"])
        context.load_verify_locations(cafile=config["client_ca"])
        self.server_bind()
        self.socket=context.wrap_socket(self.socket,server_side=True)
        self.server_activate()

    def verify_request(self,request,client_address):
        if client_address[0]!="127.0.0.1" or not self.slots.acquire(blocking=False):
            return False
        try:
            cert=request.getpeercert(binary_form=True)
            got=hashlib.sha256(cert or b"").hexdigest()
            if not cert or not hmac.compare_digest(got,self.client_fingerprint):
                self.slots.release()
                return False
            return True
        except Exception:
            self.slots.release()
            return False

    def process_request_thread(self,request,client_address):
        try:
            super().process_request_thread(request,client_address)
        finally:
            self.slots.release()


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="/etc/louksna/remote-bridge/mtls.json")
    p.add_argument("--state-dir",required=True)
    p.add_argument("--port",type=int,default=8443)
    p.add_argument("--contract",default=str(Path(__file__).with_name("CONTRACT.v0.json")))
    args=p.parse_args(argv)
    try:
        config=read_config(args.config,enforce_root=True)
        contract=json.loads(Path(args.contract).read_text())
        bridge=live_link.Transport(args.state_dir,contract)
        server=Server(bridge,config,args.port)
        try:
            bridge.ledger.append("MTLS_LOCAL_GATEWAY_STARTED",{
                "bind":"127.0.0.1","port":args.port,"remote_sudo":False,
                "root_shell":False,"certified":False})
            server.serve_forever(poll_interval=0.5)
        finally:
            server.server_close()
        return 0
    except Exception as exc:
        print(json.dumps({"status":"HOLD","reason":str(exc)[:160],
                          "root_access":False,"certified":False}),file=sys.stderr)
        return 3

if __name__=="__main__":
    sys.exit(main())
