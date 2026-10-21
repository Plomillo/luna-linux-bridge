CAPABILITY_OWNER="REPOSITORY"
FAIL_CLOSED=True
AUTHORITY_TRANSFER=False
def decide(policy_allow,unknown_effect=False,ownership_target="REPOSITORY"):
    if ownership_target!="REPOSITORY": return "DENY"
    if unknown_effect: return "HOLD"
    return "ALLOW_TO_EXECUTOR" if policy_allow else "DENY"
