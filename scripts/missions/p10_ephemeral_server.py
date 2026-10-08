#!/usr/bin/env python3
from __future__ import annotations
import json, os, signal, sys
from pathlib import Path
ROOT=Path(os.environ["MISSION_ROOT"]).resolve()
sys.path.insert(0,str(ROOT/"bridge"))
import mtls_gateway as gate
import live_link
CONTRACT=json.loads((ROOT/"bridge/CONTRACT.v0.json").read_text())
config=gate.read_config(os.environ["LOUKSNA_P10_CONFIG"],enforce_root=False)
bridge=live_link.Transport(Path(os.environ["LOUKSNA_P10_STATE"]),CONTRACT)
server=gate.Server(bridge,config,int(os.environ.get("LOUKSNA_P10_LOCAL_PORT","18443")),testing=True)
Path(os.environ["LOUKSNA_P10_READY"]).write_text(json.dumps({"bind":"127.0.0.1","port":server.server_address[1],"tls13":True})+"\n")
def stop(*_): server.shutdown()
signal.signal(signal.SIGTERM,stop)
signal.signal(signal.SIGINT,stop)
server.serve_forever(poll_interval=0.2)
