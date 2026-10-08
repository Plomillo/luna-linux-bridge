#!/usr/bin/env python3
"""Local load/stability probe for the TCP endpoint candidate."""
from __future__ import annotations
import concurrent.futures, os, socket, threading, time, hashlib

HOST=os.environ.get("TCP_ENDPOINT_HOST","127.0.0.1")
PORT=int(os.environ.get("TCP_ENDPOINT_PORT","18080"))
DURATION=float(os.environ.get("TCP_ENDPOINT_DURATION","540"))
CLIENTS=int(os.environ.get("TCP_ENDPOINT_CLIENTS","32"))
PAYLOAD=b"louksna-tcp-probe|" + b"x"*4096
errors=0
lock=threading.Lock()
sent=received=0

def client(idx):
    global errors, sent, received
    end=time.monotonic()+DURATION
    local_s=local_r=0
    while time.monotonic()<end:
        try:
            with socket.create_connection((HOST,PORT),timeout=3) as s:
                s.settimeout(3)
                for _ in range(8):
                    if time.monotonic()>=end: break
                    s.sendall(PAYLOAD)
                    local_s += len(PAYLOAD)
                    got=b""
                    while len(got)<len(PAYLOAD):
                        b=s.recv(len(PAYLOAD)-len(got))
                        if not b: raise ConnectionError("eof")
                        got+=b
                    if got!=PAYLOAD: raise ValueError("echo mismatch")
                    local_r += len(got)
        except Exception:
            with lock: errors += 1
            time.sleep(0.05)
    with lock:
        sent+=local_s; received+=local_r

start=time.monotonic()
with concurrent.futures.ThreadPoolExecutor(max_workers=CLIENTS) as ex:
    list(ex.map(client, range(CLIENTS)))
elapsed=time.monotonic()-start
print(f"PROBE duration={elapsed:.3f}s clients={CLIENTS} sent={sent} received={received} errors={errors}")
if errors or sent!=received or elapsed < DURATION*0.95:
    raise SystemExit(2)
