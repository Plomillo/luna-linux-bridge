FORBIDDEN_TRUE={"certification_authority","g23_authority","g24_authority","g23_granted","g24_granted"}
def validate_writer_record(record):
    failures=[]
    for key in FORBIDDEN_TRUE:
        if record.get(key) is True: failures.append("WRITER_AUTHORITY_FORBIDDEN:"+key)
    for key in ("provider_id","provider_version","input_sha256","output_sha256"):
        if not record.get(key): failures.append("WRITER_EVIDENCE_MISSING:"+key)
    return {"status":"PASS" if not failures else "FAIL","failures":failures}
