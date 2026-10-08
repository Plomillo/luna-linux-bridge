#!/usr/bin/env python3
from __future__ import annotations
import json, os, signal, sys
from pathlib import Path
ROOT=Path(os.environ["MISSION_ROOT"]).resolve()
sys.path.insert(0,str(ROOT/"bridge"))
import mtls_gateway as gate

class ProbeBridge:
    """Minimal transport-only bridge: no Louksna runtime, models, DB or external calls."""
    def dispatch(self, request):
        if request != {"op":"status"}:
            raise RuntimeError("P10_PROBE_ONLY_STATUS_OPERATION")
        return {
            "schema":"LRB_LOCAL_TRANSPORT/0.3",
            "status":"OBSERVATION_ONLY_UNCERTIFIED",
            "github_control":"EXTERNAL_ASYNC",
            "local_transport":"EPHEMERAL_OFF_HOST_PROBE",
            "sudo_root_shell":"NOT_EXPOSED",
            "g23":"NOT_EXECUTED",
            "g24":"NOT_EXECUTED",
            "certified":False
        }

config=gate.read_config(os.environ["LOUKSNA_P10_CONFIG"],enforce_root=False)
bridge=ProbeBridge()
server=gate.Server(bridge,config,int(os.environ.get("LOUKSNA_P10_LOCAL_PORT","18443")),testing=True)
Path(os.environ["LOUKSNA_P10_READY"]).write_text(
    json.dumps({"bind":"127.0.0.1","port":server.server_address[1],
                "tls13":True,"runtime":"TRANSPORT_PROBE_ONLY"})+"\n")
def stop(*_): server.shutdown()
signal.signal(signal.SIGTERM,stop)
signal.signal(signal.SIGINT,stop)
server.serve_forever(poll_interval=0.2)
