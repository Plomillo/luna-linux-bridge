#!/usr/bin/env python3

def plan(operation_id):
    if not operation_id:
        raise ValueError("OPERATION_ID_REQUIRED")
    return {
        "operation_id": operation_id,
        "knowledge_interface": "KNOWLEDGE_INTERFACE/1.0",
        "reasoning_interface": "REASONING_INTERFACE/1.0",
        "provider_to_provider_hard_binding": False,
        "execution_allowed": False,
    }
