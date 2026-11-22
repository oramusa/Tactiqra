import asyncio
import pytest
from fastapi import HTTPException
from app import main


def match(mid, day, home, away, competition='PD'):
    return {'id':mid,'utcDate':day,'competition':{'code':competition},'status':'FINISHED',
            'homeTeam':{'id':home,'name':str(home)},'awayTeam':{'id':away,'name':str(away)},
            'score':{'fullTime':{'home':1,'away':0}}}


def test_independent_limits_and_correct_team_scope(monkeypatch):
    calls=[]
    async def fake(team_id,limit,venue):
        calls.append((team_id,limit,venue))
        return {'teamId':team_id,'selectedCount':limit,'requestedCount':limit,'matches':[{'id':i} for i in range(limit)]}
    monkeypatch.setattr(main,'recent_matches',fake)
    result=asyncio.run(main.independent_match_windows(1,2,20,10,'home','away'))
    assert calls==[(1,20,'home'),(2,10,'away')]
    assert len(result['own']['matches'])==20
    assert len(result['opponent']['matches'])==10
    assert result['status']=='match_selection_only'


def test_unequal_coverage_does_not_invent_matches(monkeypatch):
    async def fake(team_id,limit,venue):
        return {'teamId':team_id,'selectedCount':3,'requestedCount':limit,'matches':[{'id':i} for i in range(3)]}
    monkeypatch.setattr(main,'recent_matches',fake)
    result=asyncio.run(main.independent_match_windows(1,2,20,10,'all','all'))
    assert result['own']['selectedCount']==3 and result['opponent']['selectedCount']==3
    assert result['comparison_ready']


def test_invalid_venue_and_same_team():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.independent_match_windows(1,1,20,10,'all','all'))
    assert exc.value.status_code==422
    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.independent_match_windows(1,2,20,10,'bogus','all'))
    assert exc.value.status_code==422


def test_recent_match_sort_and_venue():
    raw=[match(1,'2026-01-01',1,2),match(2,'2026-02-01',3,1),match(3,'2026-03-01',1,4),match(4,'2026-04-01',1,5,'PL')]
    assert [x['id'] for x in main.normalize_matches(raw,1,1,'all')]==[3]
    assert [x['id'] for x in main.normalize_matches(raw,1,5,'away')]==[2]
    assert [x['id'] for x in main.normalize_matches(raw,1,5,'home')]==[3,1]


def test_provider_unrelated_matches_never_enter_team_window():
    raw=[match(1,'2026-01-01',3,4),match(2,'2026-02-01',1,2)]
    assert [m['id'] for m in main.normalize_matches(raw,1,10,'all')]==[2]


def test_duplicate_match_ids_not_counted_twice():
    raw=[match(2,'2026-02-01',1,2),match(2,'2026-02-01',1,2),match(1,'2026-01-01',1,3)]
    assert [m['id'] for m in main.normalize_matches(raw,1,10,'all')]==[2,1]


def test_wrong_venue_does_not_consume_requested_slots():
    raw=[match(3,'2026-03-01',2,1),match(2,'2026-02-01',1,3),match(1,'2026-01-01',1,4)]
    assert [m['id'] for m in main.normalize_matches(raw,1,2,'home')]==[2,1]
