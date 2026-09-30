#!/usr/bin/env python3
"""GitHub read-only adapter; NEVER invokes host jobs or dispatches a mutation."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import urllib.error
import urllib.request

REPOSITORY = "Plomillo/luna-linux-bridge"
API = "https://api.github.com/repos/" + REPOSITORY
ALLOWED_ROUTES = {"/actions/runs?per_page=5", "/commits?per_page=5"}


def read_github(route, token=None, opener=urllib.request.urlopen):
    if route not in ALLOWED_ROUTES:
        raise ValueError("GITHUB_API_ROUTE_NOT_ALLOWLISTED")
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "LOUKSNA-Remote-Bridge-Readonly/0.1",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(API + route, headers=headers, method="GET")
    with opener(request, timeout=12) as response:
        content = response.read(1024 * 1024 + 1)
        if len(content) > 1024 * 1024:
            raise RuntimeError("GITHUB_RESPONSE_BUDGET_EXCEEDED")
    return json.loads(content)


def status(data):
    runs = data.get("workflow_runs", [])
    return {"schema": "LRB_GITHUB_READONLY_STATUS/0.1", "repository": REPOSITORY,
            "runs": [{"id": run.get("id"), "status": run.get("status"),
                      "conclusion": run.get("conclusion"), "head_sha": run.get("head_sha"),
                      "name": run.get("name")}
                     for run in runs[:5]], "host_execution_authorized": False,
            "github_write_authorized": False, "g23": "NOT_EXECUTED", "g24": "NOT_EXECUTED"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-status", action="store_true", required=True)
    args = parser.parse_args()
    try:
        result = status(read_github("/actions/runs?per_page=5", os.getenv("GITHUB_TOKEN")))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, RuntimeError) as exc:
        result = {"status": "HOLD_GITHUB_READONLY", "cause_type": type(exc).__name__}
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if "runs" in result else 3


if __name__ == "__main__":
    raise SystemExit(main())
