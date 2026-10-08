#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,subprocess,time,ssl,socket,ipaddress
from pathlib import Path

ROOT=Path(os.environ["MISSION_ROOT"]).resolve()
OUT=Path(os.environ.get("OUT_DIR",ROOT/"continuity/runtime-evidence/p10")).resolve(); OUT.mkdir(parents=True,exist_ok=True)
def sh(cmd,cwd=None):
    return subprocess.run(cmd,cwd=cwd,text=True,capture_output=True)
def main():
    tests=ROOT/"bridge/tests/test_mtls_gateway.py"
    if not tests.is_file(): raise RuntimeError("MTLS_TEST_SUITE_MISSING")
    r=sh(["python3","-m","unittest","bridge/tests/test_mtls_gateway.py"],cwd=ROOT)
    local={"returncode":r.returncode,"stdout":r.stdout[-6000:],"stderr":r.stderr[-6000:]}
    source=(ROOT/"bridge/mtls_gateway.py").read_text()
    tls13="ssl.TLSVersion.TLSv1_3" in source
    loopback='super().__init__(("127.0.0.1",port)' in source
    remote_host=os.environ.get("LOUKSNA_REMOTE_RELAY_HOST")
    remote_port=int(os.environ.get("LOUKSNA_REMOTE_RELAY_PORT","0") or "0")
    ca=os.environ.get("LOUKSNA_MTLS_CA_FILE"); cert=os.environ.get("LOUKSNA_MTLS_CLIENT_CERT_FILE"); key=os.environ.get("LOUKSNA_MTLS_CLIENT_KEY_FILE")
    expected_pin=os.environ.get("LOUKSNA_REMOTE_SERVER_CERT_SHA256","").lower()
    server_name=os.environ.get("LOUKSNA_REMOTE_SERVER_NAME",remote_host)
    remote={}
    if remote_host and remote_port and ca and cert and key:
        try:
            try: resolved=ipaddress.ip_address(socket.gethostbyname(remote_host))
            except ValueError: resolved=None
            if remote_host in {"localhost","localhost.localdomain"} or (resolved and (resolved.is_loopback or resolved.is_private or resolved.is_link_local)):
                raise RuntimeError("REMOTE_RELAY_MUST_BE_OFF_HOST")
            if not (1<=remote_port<=65535): raise RuntimeError("REMOTE_RELAY_PORT_INVALID")
            if not expected_pin or len(expected_pin)!=64: raise RuntimeError("REMOTE_SERVER_CERT_PIN_REQUIRED")
            ctx=ssl.create_default_context(ssl.Purpose.SERVER_AUTH,cafile=ca)
            ctx.minimum_version=ssl.TLSVersion.TLSv1_3; ctx.maximum_version=ssl.TLSVersion.TLSv1_3
            ctx.load_cert_chain(cert,key)
            mode=os.environ.get("LOUKSNA_REMOTE_PROBE_MODE","HTTP_STATUS").upper()
            def probe():
                with socket.create_connection((remote_host,remote_port),timeout=8) as raw:
                    with ctx.wrap_socket(raw,server_hostname=server_name) as s:
                        if s.version()!="TLSv1.3": raise RuntimeError("REMOTE_TLS_VERSION_INVALID")
                        peer=hashlib.sha256(s.getpeercert(binary_form=True)).hexdigest()
                        if peer!=expected_pin: raise RuntimeError("REMOTE_SERVER_CERT_PIN_MISMATCH")
                        if mode=="TLS_ECHO":
                            payload=b"LOUKSNA_P10_TRANSPORT_ECHO/1"
                            s.sendall(payload)
                            data=b""
                            while len(data)<len(payload):
                                block=s.recv(len(payload)-len(data))
                                if not block: break
                                data+=block
                            if data!=payload: raise RuntimeError("REMOTE_ECHO_ROUNDTRIP_FAILURE")
                            return {"mode":mode,"tls_version":s.version(),"peer_cert_sha256":peer,"server_name":server_name,"peer":s.getpeername(),"bytes":len(data),"roundtrip_sha256":hashlib.sha256(data).hexdigest()}
                        s.sendall(b"GET /v1/status HTTP/1.0\\r\\nHost: "+remote_host.encode()+b"\\r\\nConnection: close\\r\\n\\r\\n")
                        data=b""
                        while True:
                            block=s.recv(8192)
                            if not block: break
                            data+=block
                        if b"200 OK" not in data.split(b"\\r\\n",1)[0]: raise RuntimeError("REMOTE_STATUS_HTTP_FAILURE")
                        return {"mode":mode,"tls_version":s.version(),"peer_cert_sha256":peer,"server_name":server_name,"peer":s.getpeername(),"bytes":len(data)}
            remote["mode"]=mode
            remote["first"]=probe(); time.sleep(1); remote["reconnect"]=probe(); remote["status"]="PASS"
        except Exception as exc:
            remote={"status":"FAIL","error":type(exc).__name__+":"+str(exc)}
    else:
        remote={"status":"NOT_CONFIGURED"}
    proven=(remote.get("status")=="PASS" and tls13 and loopback)
    evidence={"schema":"LOUKSNA_ZD_P10_TRANSPORT/1.0","status":"PASS" if proven else "HOLD","local_mtls_test":local,"tls13_source_gate":tls13,"loopback_binding_source_gate":loopback,"off_host_relay_host_configured":bool(remote_host),"off_host_relay_materially_proven":proven,"remote_probe":remote,"blocker":None if proven else "P10_OFF_HOST_RELAY_UNPROVEN","reason":"Off-host relay is proven only when the remote endpoint completes the pinned TLS 1.3 mTLS handshake and the configured transport/application probe twice."}
    (OUT/"P10_TRANSPORT_EVIDENCE.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    result={"status":"PASS" if proven else "HOLD_INDEPENDENT_CONTINUATION","checkpoint":"CHECKPOINT_10" if proven else "CHECKPOINT_10","parent_checkpoint":"CHECKPOINT_09","next_point":"P11" if not proven else "P11","transition_id":"P10-TO-P11-001" if proven else "P10-HOLD-TO-P11-INDEPENDENT-001","certified":False,"active":False,"g23":"SEPARATE_REQUIRED","g24":"SEPARATE_REQUIRED","open_blockers":[] if proven else ["P10_OFF_HOST_RELAY_UNPROVEN"],"material_evidence":evidence}
    (ROOT/"continuity/CONTINUATION_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("LOUKSNA_P10_TELEMETRY "+json.dumps({"event":"CHECKPOINT_10_PASS" if proven else "CHECKPOINT_10_HOLD","next_point":"P11","status":result["status"],"blocker":None if proven else "P10_OFF_HOST_RELAY_UNPROVEN","off_host_relay_materially_proven":proven},sort_keys=True),flush=True)
if __name__=="__main__":
    try: main()
    except Exception as e: print("P10_FAIL_CLOSED "+type(e).__name__+": "+str(e),file=__import__("sys").stderr); raise
