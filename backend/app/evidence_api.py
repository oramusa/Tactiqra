"""Read-only historical pilot evidence API."""
import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
router = APIRouter(prefix="/api/v1/evidence", tags=["historical-evidence"])

def load_report():
    path_value = os.getenv("FOOTBALLIQ_PILOT_REPORT")
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_file() or path.stat().st_size > 8_000_000:
        raise HTTPException(503, "Historical report unavailable")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise HTTPException(503, "Invalid historical report")
    if not isinstance(data, dict) or not isinstance(data.get("transitions"), list):
        raise HTTPException(503, "Invalid historical report structure")
    if len(data["transitions"]) > 100_000:
        raise HTTPException(503, "Pilot report contains too many transitions")
    # Reject inconsistent report metadata rather than displaying misleading figures.
    if not isinstance(data.get("match_id"), (str, int)) or not str(data["match_id"]).strip():
        raise HTTPException(503, "Missing match provenance")
    count = data.get("event_count")
    if type(count) is not int or count < 0:
        raise HTTPException(503, "Invalid event count")
    for t in data["transitions"]:
        if not isinstance(t, dict):
            raise HTTPException(503, "Invalid transition entry")
        ids = t.get("evidence_event_ids")
        if not isinstance(ids, list) or len(ids) > 200 or any(type(v) not in (str, int) or not str(v).strip() for v in ids):
            raise HTTPException(503, "Invalid evidence event IDs")
        if t.get("verification_status") not in ("provisional", "provisional_verified", "needs_review"):
            raise HTTPException(503, "Missing transition verification status")
        if "match_id" in t and str(t["match_id"]) != str(data["match_id"]):
            raise HTTPException(503, "Cross-match evidence is not allowed")
    return data

@router.get("/review-export")
def review_export(limit: int = Query(10, ge=1, le=100)):
    """Export the SAME deterministic candidate selection as the offline pipeline."""
    import csv
    import io
    from fastapi.responses import Response
    from review_export import FIELDS, select_review_cases, spreadsheet_safe
    report = load_report()
    if report is None:
        raise HTTPException(404, "No historical pilot report configured")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows([{k: spreadsheet_safe(v) for k, v in row.items()} for row in select_review_cases(report, limit)])
    return Response(content=output.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="footballiq_manual_review.csv"',
                             "Cache-Control": "no-store"})

@router.get("/summary")
def summary():
    r=load_report()
    if r is None:
        return {"status":"insufficient_data","reason":"No historical report configured","match_id":None,"event_count":None,"transition_count":None}
    return {"status":"provisional_unreviewed","match_id":str(r.get("match_id","")),"event_count":r.get("event_count"),"transition_count":len(r["transitions"]),"source":"local_historical_report","provisional":True,"warning":"Historical pilot only; not independently validated."}

@router.get("/transitions")
def transitions(limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0)):
    r=load_report()
    if r is None:
        return {"status":"insufficient_data","total":0,"items":[]}
    keys=("match_id","period","start_event_id","losing_team_id","gaining_team_id","window_seconds","shot","goal","evidence_event_ids","end_reason","verification_status","algorithm_version")
    items=[]
    for t in r["transitions"][offset:offset+limit]:
        items.append({k:t.get(k) for k in keys})
    return {"status":"provisional_unreviewed","match_id":str(r.get("match_id","")),"total":len(r["transitions"]),"items":items}


@router.get("/review-quality")
def review_quality():
    """Read-only, independently prepared review outcome. Never infer quality from candidates."""
    report = load_report()
    if report is None:
        return {"status": "insufficient_data", "sample_precision": None, "reviewed_count": 0,
                "recall_measured": False}
    configured = os.getenv("FOOTBALLIQ_REVIEW_QUALITY")
    if not configured:
        return {"status": "review_not_submitted", "sample_precision": None,
                "reviewed_count": 0, "recall_measured": False}
    path = Path(configured)
    if not path.is_file() or path.stat().st_size > 100_000:
        raise HTTPException(503, "Review quality file unavailable")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError, UnicodeError):
        raise HTTPException(503, "Invalid review quality file")
    if not isinstance(data, dict) or str(data.get("match_id")) != str(report["match_id"]):
        raise HTTPException(503, "Review and report match IDs disagree")
    reviewed = data.get("reviewed_count")
    conclusive = data.get("sample_precision_denominator")
    correct = data.get("correct_count")
    false_positive = data.get("false_positive_count")
    uncertain = data.get("uncertain_count")
    if any(type(x) is not int or x < 0 for x in (reviewed, conclusive, correct, false_positive, uncertain)):
        raise HTTPException(503, "Invalid review counts")
    if correct + false_positive != conclusive or conclusive + uncertain != reviewed or reviewed > len(report["transitions"]):
        raise HTTPException(503, "Inconsistent review counts")
    expected = round(correct / conclusive, 4) if conclusive else None
    if data.get("sample_precision") != expected or data.get("recall_measured") is not False or data.get("independent_full_match_accuracy_measured") is not False:
        raise HTTPException(503, "Inconsistent review quality assertions")
    return {"status": "sample_review_complete" if reviewed >= 10 and conclusive else "review_incomplete",
            "match_id": str(report["match_id"]), "reviewed_count": reviewed,
            "correct_count": correct, "false_positive_count": false_positive,
            "uncertain_count": uncertain, "sample_precision_denominator": conclusive,
            "sample_precision": expected, "recall_measured": False,
            "warning": "Only reviewed candidate precision; not recall or full-match accuracy."}
