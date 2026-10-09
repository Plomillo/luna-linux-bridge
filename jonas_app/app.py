#!/usr/bin/env python3
"""Jonas budget, accounting and telemetry MVP. Python standard library only."""
from __future__ import annotations
import hashlib, json, os, sqlite3, threading, time
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("JONAS_DB", ROOT / "jonas.sqlite3"))
HOST = os.environ.get("JONAS_HOST", "127.0.0.1")
PORT = int(os.environ.get("JONAS_PORT", "8765"))
DB_LOCK = threading.RLock()
MICRO = Decimal("1000000")

def micros(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("amount must be a decimal number")
    if not amount.is_finite() or amount < 0:
        raise ValueError("amount must be finite and non-negative")
    scaled = amount * MICRO
    if scaled != scaled.to_integral_value():
        raise ValueError("amount supports at most 6 decimal places")
    return int(scaled)

def dollars(value):
    return format(Decimal(value) / MICRO, ".6f").rstrip("0").rstrip(".") or "0"

def connect():
    con = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS budgets (
          id TEXT PRIMARY KEY, limit_micro INTEGER NOT NULL CHECK(limit_micro >= 0),
          reserve_micro INTEGER NOT NULL CHECK(reserve_micro >= 0),
          spent_micro INTEGER NOT NULL DEFAULT 0 CHECK(spent_micro >= 0),
          halted INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL,
          CHECK(reserve_micro <= limit_micro)
        );
        CREATE TABLE IF NOT EXISTS ledger (
          id INTEGER PRIMARY KEY AUTOINCREMENT, budget_id TEXT NOT NULL REFERENCES budgets(id),
          idempotency_key TEXT NOT NULL, amount_micro INTEGER NOT NULL,
          category TEXT NOT NULL, note TEXT NOT NULL, created_at REAL NOT NULL,
          UNIQUE(budget_id, idempotency_key)
        );
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, payload TEXT NOT NULL,
          previous_hash TEXT NOT NULL, digest TEXT NOT NULL, created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS savings_evaluations (
          id INTEGER PRIMARY KEY AUTOINCREMENT, baseline_micro INTEGER NOT NULL,
          candidate_micro INTEGER NOT NULL, quality_pass INTEGER NOT NULL,
          critical_regression INTEGER NOT NULL, net_savings_pct TEXT NOT NULL,
          accepted INTEGER NOT NULL, created_at REAL NOT NULL
        );
        """)

def event(con, kind, payload):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    row = con.execute("SELECT digest FROM events ORDER BY id DESC LIMIT 1").fetchone()
    previous = row["digest"] if row else "GENESIS"
    digest = hashlib.sha256((previous + "\n" + kind + "\n" + raw).encode()).hexdigest()
    con.execute("INSERT INTO events(kind,payload,previous_hash,digest,created_at) VALUES(?,?,?,?,?)",
                (kind, raw, previous, digest, time.time()))
    return digest

def budget_status(con, row):
    spent = row["spent_micro"]
    available = row["limit_micro"] - row["reserve_micro"] - spent
    return {"id": row["id"], "limit": dollars(row["limit_micro"]),
            "reserve": dollars(row["reserve_micro"]), "spent": dollars(spent),
            "available_for_spend": dollars(max(0, available)),
            "halted": bool(row["halted"]),
            "over_budget": spent > row["limit_micro"] - row["reserve_micro"]}

def verify_chain(con):
    previous = "GENESIS"
    for row in con.execute("SELECT * FROM events ORDER BY id"):
        expected = hashlib.sha256((previous + "\n" + row["kind"] + "\n" + row["payload"]).encode()).hexdigest()
        if row["previous_hash"] != previous or row["digest"] != expected:
            return {"valid": False, "failed_event_id": row["id"]}
        previous = row["digest"]
    return {"valid": True, "events": con.execute("SELECT COUNT(*) FROM events").fetchone()[0]}

def dispatch(method, path, body):
    with DB_LOCK, connect() as con:
        if method == "GET" and path == "/api/health":
            return 200, {"ok": True, "service": "jonas-budget-telemetry"}
        if method == "GET" and path == "/api/budgets":
            rows = con.execute("SELECT * FROM budgets ORDER BY created_at DESC").fetchall()
            return 200, {"budgets": [budget_status(con, r) for r in rows]}
        if method == "POST" and path == "/api/budgets":
            bid = str(body.get("id", "")).strip()
            if not bid or len(bid) > 100:
                return 400, {"error": "id is required (max 100 chars)"}
            limit, reserve = micros(body.get("limit")), micros(body.get("reserve", 0))
            if limit <= 0 or reserve >= limit:
                return 400, {"error": "limit must be positive and reserve must be smaller than limit"}
            con.execute("BEGIN IMMEDIATE")
            try:
                con.execute("INSERT INTO budgets(id,limit_micro,reserve_micro,created_at) VALUES(?,?,?,?)",
                            (bid, limit, reserve, time.time()))
                event(con, "budget.created", {"id": bid, "limit": limit, "reserve": reserve})
                con.execute("COMMIT")
            except sqlite3.IntegrityError:
                con.execute("ROLLBACK")
                return 409, {"error": "budget id already exists"}
            except Exception:
                con.execute("ROLLBACK")
                raise
            return 201, {"budget": budget_status(con, con.execute("SELECT * FROM budgets WHERE id=?", (bid,)).fetchone())}
        if method == "POST" and path.startswith("/api/budgets/") and path.endswith("/spend"):
            bid = path.split("/")[3]
            key = str(body.get("idempotency_key", "")).strip()
            category = str(body.get("category", "unspecified"))[:100]
            note = str(body.get("note", ""))[:500]
            if not key or len(key) > 200:
                return 400, {"error": "idempotency_key is required (max 200 chars)"}
            amount = micros(body.get("amount"))
            if amount <= 0:
                return 400, {"error": "amount must be greater than zero"}
            con.execute("BEGIN IMMEDIATE")
            try:
                row = con.execute("SELECT * FROM budgets WHERE id=?", (bid,)).fetchone()
                if row is None:
                    con.execute("ROLLBACK")
                    return 404, {"error": "budget not found"}
                existing = con.execute("SELECT * FROM ledger WHERE budget_id=? AND idempotency_key=?", (bid,key)).fetchone()
                if existing:
                    con.execute("COMMIT")
                    return 200, {"duplicate": True, "entry_id": existing["id"], "budget": budget_status(con, row)}
                if row["halted"]:
                    con.execute("ROLLBACK")
                    return 423, {"error": "budget halted; spend denied"}
                remaining = row["limit_micro"] - row["reserve_micro"] - row["spent_micro"]
                if amount > remaining:
                    event(con, "spend.denied", {"budget_id": bid, "amount": amount, "reason": "limit_or_reserve"})
                    con.execute("COMMIT")
                    return 409, {"error": "spend denied: would breach limit or protected reserve",
                                 "budget": budget_status(con, row)}
                cur = con.execute("INSERT INTO ledger(budget_id,idempotency_key,amount_micro,category,note,created_at) VALUES(?,?,?,?,?,?)",
                                  (bid,key,amount,category,note,time.time()))
                con.execute("UPDATE budgets SET spent_micro=spent_micro+? WHERE id=?", (amount,bid))
                event(con, "spend.recorded", {"budget_id": bid, "entry_id": cur.lastrowid,
                                              "amount": amount, "idempotency_key": key})
                con.execute("COMMIT")
            except Exception:
                if con.in_transaction: con.execute("ROLLBACK")
                raise
            row = con.execute("SELECT * FROM budgets WHERE id=?", (bid,)).fetchone()
            return 201, {"entry_id": cur.lastrowid, "budget": budget_status(con,row)}
        if method == "POST" and path.startswith("/api/budgets/") and path.endswith("/halt"):
            bid = path.split("/")[3]
            row = con.execute("SELECT * FROM budgets WHERE id=?", (bid,)).fetchone()
            if row is None: return 404, {"error": "budget not found"}
            con.execute("BEGIN IMMEDIATE")
            con.execute("UPDATE budgets SET halted=1 WHERE id=?", (bid,))
            event(con, "budget.halted", {"budget_id": bid})
            con.execute("COMMIT")
            return 200, {"halted": True, "budget_id": bid}
        if method == "POST" and path.startswith("/api/budgets/") and path.endswith("/resume"):
            bid = path.split("/")[3]
            if body.get("confirm") is not True:
                return 400, {"error": "explicit confirm=true is required"}
            row = con.execute("SELECT * FROM budgets WHERE id=?", (bid,)).fetchone()
            if row is None: return 404, {"error": "budget not found"}
            con.execute("BEGIN IMMEDIATE")
            con.execute("UPDATE budgets SET halted=0 WHERE id=?", (bid,))
            event(con, "budget.resumed", {"budget_id": bid, "explicit_confirmation": True})
            con.execute("COMMIT")
            return 200, {"halted": False, "budget_id": bid}
        if method == "GET" and path == "/api/telemetry":
            events = [dict(r) for r in con.execute("SELECT id,kind,payload,previous_hash,digest,created_at FROM events ORDER BY id DESC LIMIT 100")]
            for e in events: e["payload"] = json.loads(e["payload"])
            return 200, {"events": events, "chain": verify_chain(con)}
        if method == "POST" and path == "/api/savings/evaluate":
            baseline, candidate = micros(body.get("baseline_cost")), micros(body.get("candidate_cost"))
            quality = body.get("quality_pass") is True
            regression = body.get("critical_regression") is True
            if baseline <= 0:
                return 400, {"error": "baseline_cost must be positive"}
            pct = (Decimal(baseline - candidate) / Decimal(baseline)) * Decimal(100)
            accepted = pct >= Decimal(10) and quality and not regression
            con.execute("BEGIN IMMEDIATE")
            con.execute("INSERT INTO savings_evaluations(baseline_micro,candidate_micro,quality_pass,critical_regression,net_savings_pct,accepted,created_at) VALUES(?,?,?,?,?,?,?)",
                        (baseline,candidate,int(quality),int(regression),str(pct.quantize(Decimal("0.01"))),int(accepted),time.time()))
            event(con, "savings.evaluated", {"baseline": baseline, "candidate": candidate,
                  "net_savings_pct": str(pct.quantize(Decimal("0.01"))), "quality_pass": quality,
                  "critical_regression": regression, "accepted": accepted})
            con.execute("COMMIT")
            return 200, {"net_savings_percent": str(pct.quantize(Decimal("0.01"))),
                         "accepted": accepted, "reason": "passed" if accepted else
                         "requires >=10% net savings, quality_pass=true and critical_regression=false"}
        return 404, {"error": "endpoint not found"}

class Handler(BaseHTTPRequestHandler):
    def _send(self, status, data, content_type="application/json; charset=utf-8"):
        raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw))); self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8"); return
        try: status, data = dispatch("GET", path, {})
        except Exception as e: status, data = 500, {"error": "internal error", "detail": str(e)}
        self._send(status, data)
    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > 65536: self._send(413, {"error":"request too large"}); return
            body = json.loads(self.rfile.read(size) or b"{}")
            if not isinstance(body, dict): raise ValueError("JSON object required")
            status, data = dispatch("POST", urlparse(self.path).path, body)
        except (ValueError, json.JSONDecodeError) as e: status, data = 400, {"error": str(e)}
        except Exception as e: status, data = 500, {"error":"internal error", "detail":str(e)}
        self._send(status, data)
    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

if __name__ == "__main__":
    init_db()
    print(f"Jonas Budget & Telemetry running at http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
