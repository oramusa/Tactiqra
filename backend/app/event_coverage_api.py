"""Auditable event-data coverage; never infer identity from team names or dates."""
import hashlib
import json
import os
from datetime import date
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/v1/opponentiq", tags=["event-coverage"])
MAX_BYTES = 30_000_000

def identity_metadata(entry):
    """Explicit cross-provider mapping metadata, not an independent identity certificate."""
    identity = entry.get("identity")
    if not isinstance(identity, dict):
        return None
    fields = ("event_match_id", "metadata_source", "match_date", "competition")
    if any(not isinstance(identity.get(k), str) or not identity[k].strip() or len(identity[k]) > 500 for k in fields):
        return None
    if identity["competition"] != "PD":
        return None
    try:
        if date.fromisoformat(identity["match_date"]).isoformat() != identity["match_date"]:
            return None
    except ValueError:
        return None
    for k in ("home_team_id", "away_team_id", "home_goals", "away_goals"):
        if type(identity.get(k)) is not int or identity[k] < (1 if k.endswith("_id") else 0):
            return None
    if identity["home_team_id"] == identity["away_team_id"]:
        return None
    return {k: identity[k] for k in (*fields, "home_team_id", "away_team_id", "home_goals", "away_goals")}


def audit_manifest(match_ids: list[int], manifest_path: Path):
    """Manifest entries require provider match id, source id, relative file and SHA-256."""
    try:
        if not manifest_path.is_file() or manifest_path.stat().st_size > 2_000_000:
            raise ValueError("Manifest unavailable or too large")
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict) or not isinstance(doc.get("matches"), list):
            raise ValueError("Invalid manifest format")
    except (OSError, ValueError, UnicodeError) as exc:
        raise HTTPException(503, "Event coverage manifest unavailable or invalid") from exc
    entries = {}
    for entry in doc["matches"]:
        if not isinstance(entry, dict):
            continue
        mid = entry.get("provider_match_id")
        if type(mid) is not int or mid <= 0:
            continue
        entries.setdefault(mid, []).append(entry)
    event_keys = {}
    for group in entries.values():
        for entry in group:
            meta = identity_metadata(entry)
            if meta and isinstance(entry.get('event_source'), str):
                key = (entry['event_source'], meta['event_match_id'])
                event_keys[key] = event_keys.get(key, 0) + 1
    base = manifest_path.resolve().parent
    results = []
    for mid in dict.fromkeys(match_ids):
        matches = entries.get(mid, [])
        status, reason, source = "missing", "No explicit match mapping", None
        if len(matches) > 1:
            status, reason = "invalid", "Duplicate provider match mappings"
        elif matches:
            entry = matches[0]
            source = entry.get("event_source") if isinstance(entry.get("event_source"), str) else None
            rel = entry.get("relative_path")
            digest = entry.get("sha256")
            if not source or not isinstance(rel, str) or not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
                status, reason = "invalid", "Missing or invalid provenance fields"
            else:
                path = (base / rel).resolve()
                if not path.is_relative_to(base) or not path.is_file() or path.stat().st_size > MAX_BYTES:
                    status, reason = "invalid", "Event file missing, unsafe or too large"
                elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    status, reason = "invalid", "Event file checksum mismatch"
                else:
                    try:
                        data = json.loads(path.read_text(encoding="utf-8"))
                        if not isinstance(data, list):
                            raise ValueError()
                        status, reason = "verified_file", "File integrity verified; tactical correctness not validated"
                    except (ValueError, OSError, UnicodeError):
                        status, reason = "invalid", "Invalid event JSON"
        meta = identity_metadata(matches[0]) if len(matches) == 1 else None
        identity_status = "metadata_missing"
        if meta:
            identity_status = "ambiguous" if event_keys.get((source, meta["event_match_id"]), 0) != 1 else "metadata_available"
        results.append({"providerMatchId": mid, "status": status, "reason": reason, "eventSource": source,
                        "identityStatus": identity_status, "identity": meta if identity_status == "metadata_available" else None})
    verified = sum(x["status"] == "verified_file" for x in results)
    return {"requested": len(results), "verifiedFiles": verified, "missingOrInvalid": len(results)-verified,
            "matches": results, "warning": "Explicit manifest and checksum verification only; does not establish provider ID equivalence or tactical validity."}

@router.get("/event-coverage")
def event_coverage(match_ids: str = Query(..., min_length=1, max_length=1000)):
    try:
        ids = [int(x) for x in match_ids.split(",")]
    except ValueError as exc:
        raise HTTPException(422, "match_ids must be comma-separated positive integers") from exc
    if not 1 <= len(ids) <= 100 or any(x <= 0 for x in ids):
        raise HTTPException(422, "Provide 1–100 positive match IDs")
    configured = os.getenv("FOOTBALLIQ_EVENT_MANIFEST")
    if not configured:
        return {"status": "not_configured", "requested": len(set(ids)), "verifiedFiles": 0,
                "warning": "No event manifest configured; scoreline matches are not tactical event coverage."}
    return {"status": "audited", **audit_manifest(ids, Path(configured))}
