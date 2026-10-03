#!/usr/bin/env python3

COOPERATION_SCHEMA = "LOUKSNA_KNOWLEDGE_REASONING_COOPERATION/1.0"

def bind(reasoning_request, knowledge_binding):
    if reasoning_request.get("schema") != "LOUKSNA_REASONING_REQUEST/1.0":
        raise ValueError("REASONING_REQUEST_SCHEMA_INVALID")
    if knowledge_binding.get("interface") != "KNOWLEDGE_INTERFACE/1.0":
        raise ValueError("KNOWLEDGE_INTERFACE_INVALID")
    out=dict(reasoning_request)
    context=dict(out.get("context") or {})
    if "knowledge_binding" in context:
        raise ValueError("DUPLICATE_KNOWLEDGE_BINDING")
    context["knowledge_binding"]=dict(knowledge_binding)
    out["context"]=context
    return out
