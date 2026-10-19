"""Public stand-in: the claim watch list ties sentences of the private working documents to the registry; not published."""
from __future__ import annotations


def build_watch(registry: dict) -> dict:
    return {"claims_failing": [], "_meta": {"claims_failing": 0, "note": "claim watch list is not part of the public repository"}}
