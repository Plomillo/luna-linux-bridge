#!/usr/bin/env python3
"""Pinned adapter for hardened promotion of the certified main recovery root."""
import json
if __name__=="__main__":
    print(json.dumps({
      "adapter":"MAIN_RECOVERY_ROOT_HARDENED_PROMOTION_V1",
      "mission_sha256":"03c0c6013d1d0aedbde6203aa804b65a08c79aefbc019624577ca732a60ffc17",
      "execution":"DEDICATED_GOVERNED_WORKFLOW_DISPATCH",
      "material_effect":True,
      "target":"MAIN",
      "candidate_sha":"2a5057a2b47c122476a8fc90b756fdf8d942ebc5",
      "expected_main_sha":"48b42b6bc985450c380c601d07ac1285e1e755f5"
    },sort_keys=True))
