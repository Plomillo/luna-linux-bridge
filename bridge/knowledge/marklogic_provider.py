#!/usr/bin/env python3

def bind_material(image_ref, repo_digest, image_id, main_commit):
    if not image_ref.startswith("progressofficial/marklogic-db:"):
        raise ValueError("UNAPPROVED_PROVIDER")
    if "@sha256:" not in repo_digest:
        raise ValueError("UNPINNED_DIGEST")
    return {
        "provider_id": "MARKLOGIC_12",
        "provider_class": "SWAPPABLE_KNOWLEDGE_PROVIDER",
        "image_ref": image_ref,
        "repo_digest": repo_digest,
        "image_id": image_id,
        "acquisition_root_ref": "main",
        "main_commit": main_commit,
        "canonical_authority": False,
        "execution_authority": False,
        "certification_authority": False,
        "activation": False,
    }
