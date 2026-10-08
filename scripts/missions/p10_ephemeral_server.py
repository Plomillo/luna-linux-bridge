#!/usr/bin/env python3
from __future__ import annotations
import hashlib, hmac, json, os, signal, socketserver, ssl, sys
from pathlib import Path
ROOT=Path(os.environ["MISSION_ROOT"]).resolve()

class EchoHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(8)
        while True:
            data=self.request.recv(4096)
            if not data:
                return
            self.request.sendall(data)

class EchoServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads=True
    allow_reuse_address=True
    request_queue_size=3
    def __init__(self,config,port):
        self.slots=__import__("threading").BoundedSemaphore(3)
        self.client_fingerprint=config["client_cert_sha256"]
        super().__init__(("127.0.0.1",port),EchoHandler,bind_and_activate=False)
        self.allow_reuse_address=True
        self.server_bind(); self.server_activate()
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version=ssl.TLSVersion.TLSv1_3
        ctx.maximum_version=ssl.TLSVersion.TLSv1_3
        ctx.verify_mode=ssl.CERT_REQUIRED
        ctx.load_cert_chain(config["server_cert"],config["server_key"])
        ctx.load_verify_locations(cafile=config["client_ca"])
        self.socket=ctx.wrap_socket(self.socket,server_side=True)
    def verify_request(self,request,client_address):
        if not self.slots.acquire(blocking=False):
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

cfg=json.loads(Path(os.environ["LOUKSNA_P10_CONFIG"]).read_text())
server=EchoServer(cfg,int(os.environ.get("LOUKSNA_P10_LOCAL_PORT","18443")))
Path(os.environ["LOUKSNA_P10_READY"]).write_text(
    json.dumps({"bind":"127.0.0.1","port":server.server_address[1],
                "tls13":True,"runtime":"TRANSPORT_TLS_ECHO_ONLY"})+"\n")
def stop(*_): server.shutdown()
signal.signal(signal.SIGTERM,stop)
signal.signal(signal.SIGINT,stop)
server.serve_forever(poll_interval=0.2)
