def retry_allowed(effect_known,idempotent,state):
    return bool(effect_known and idempotent and state not in {"HOLD","FAILED"})
def next_state(event,current="PROGRESSING"):
    if event=="UNKNOWN_EFFECT": return "HOLD"
    if event=="NO_FORWARD_PROGRESS": return "DIAGNOSING"
    if event=="RESOURCE_RED": return "AT_RISK"
    return current
