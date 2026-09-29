#!/usr/bin/env python3
"""Pinned declarative adapter for exact LUNA R4 PART1 differential resume mission."""
import json
SOURCE_SHA256 = "4820cf7d5ca873f5917466a76e9b57fd46f84344a4a9f1fa3e47d144e9a01456"
MISSION_CLASS = "LUNA_R4_PART1_DIFFERENTIAL_RESUME"
SCOPE = "LUNA_R4_PART1_DIFFERENTIAL_RESUME_HANDOFF"
print(json.dumps({"status":"READY","source_sha256":SOURCE_SHA256,"mission_class":MISSION_CLASS,"scope":SCOPE},sort_keys=True))
