#!/usr/bin/env python3
"""Minimal TCP endpoint candidate: transport/echo only.

No Louksna imports, no TLS termination, no HTTP, no external services.
Telemetry is emitted as JSONL with a SHA-256 hash chain.
"""
from __future__ import annotations
import hashlib, json, os, signal, socket, socketserver, threading, time, resource
from pathlib import Path

HOST = os.environ.get("TCP_ENDPOINT_HOST", "127.0.0.1")
PORT = int(os.environ.get("TCP_ENDPOINT_PORT", "18080"))
BUDGET_BYTES = 1024 * 1024 * 1024
TELEMETRY_SECONDS = float(os.environ.get("TCP_ENDPOINT_TELEMETRY_SECONDS", "5"))
IDLE_TIMEOUT = float(os.environ.get("TCP_ENDPOINT_IDLE_TIMEOUT", "15"))
MAX_CONNECTIONS = int(os.environ.get("TCP_ENDPOINT_MAX_CONNECTIONS", "128"))
MAX_BUFFER = int(os.environ.get("TCP_ENDPOINT_MAX_BUFFER", str(64 * 1024)))
LOG_PATH = Path(os.environ.get("TCP_ENDPOINT_LOG", "tcp-endpoint-telemetry.jsonl"))

stop = threading.Event()
active = 0
active_lock = threading.Lock()
peak_active = 0
bytes_rx = 0
bytes_tx = 0
counters_lock = threading.Lock()
prev_cpu = time.process_time()
prev_wall = time.monotonic()
prev_hash = "0" * 64
emit_lock = threading.Lock()

def rss_bytes() -> int:
    # Linux ru_maxrss is KiB. Use current VmRSS when available.
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    except Exception:
        pass
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024

def cpu_pct() -> float:
    global prev_cpu, prev_wall
    now_cpu, now_wall = time.process_time(), time.monotonic()
    dc, dw = now_cpu - prev_cpu, now_wall - prev_wall
    prev_cpu, prev_wall = now_cpu, now_wall
    return round(max(0.0, min(100.0, (dc / dw) * 100.0 if dw else 0.0)), 3)

def emit(event: str, **fields):
    global prev_hash
    with emit_lock:
        rec = {
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": event,
        "pid": os.getpid(),
        "rss_bytes": rss_bytes(),
        "budget_bytes": BUDGET_BYTES,
        "budget_used_pct": round(rss_bytes() * 100.0 / BUDGET_BYTES, 6),
        **fields,
    }
    rec["prev_hash"] = prev_hash
        canonical = json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()
        rec["entry_hash"] = hashlib.sha256(canonical).hexdigest()
        prev_hash = rec["entry_hash"]
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())

class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        global active, peak_active, bytes_rx, bytes_tx
        with active_lock:
            if active >= MAX_CONNECTIONS:
                emit("connection_rejected", reason="max_connections")
                return
            active += 1
            peak_active = max(peak_active, active)
        try:
            self.request.settimeout(IDLE_TIMEOUT)
            emit("connection_open", peer=str(self.client_address), active=active)
            while not stop.is_set():
                data = self.request.recv(MAX_BUFFER)
                if not data:
                    break
                with counters_lock:
                    bytes_rx += len(data)
                self.request.sendall(data)
                with counters_lock:
                    bytes_tx += len(data)
        except (socket.timeout, ConnectionError, OSError) as exc:
            emit("connection_end", peer=str(self.client_address), reason=type(exc).__name__)
        finally:
            with active_lock:
                active -= 1
            emit("connection_close", peer=str(self.client_address), active=active)

class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 64

def telemetry(server):
    while not stop.wait(TELEMETRY_SECONDS):
        with active_lock:
            a, p = active, peak_active
        with counters_lock:
            rx, tx = bytes_rx, bytes_tx
        rss = rss_bytes()
        emit("pulse", active_connections=a, peak_connections=p,
             bytes_rx=rx, bytes_tx=tx, cpu_pct=cpu_pct(),
             headroom_bytes=max(0, BUDGET_BYTES-rss),
             budget_status="WITHIN_BUDGET" if rss <= BUDGET_BYTES else "OVER_BUDGET")

def shutdown(*_):
    stop.set()

def main():
    global prev_hash
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, shutdown)
    LOG_PATH.unlink(missing_ok=True)
    emit("startup", host=HOST, port=PORT, budget_bytes=BUDGET_BYTES,
         telemetry_seconds=TELEMETRY_SECONDS, max_connections=MAX_CONNECTIONS,
         max_buffer=MAX_BUFFER)
    server = Server((HOST, PORT), Handler)
    t = threading.Thread(target=telemetry, args=(server,), daemon=True)
    t.start()
    emit("ready")
    try:
        while not stop.is_set():
            server.handle_request()
    finally:
        server.server_close()
        emit("shutdown")

if __name__ == "__main__":
    main()
