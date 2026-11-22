import asyncio
from types import SimpleNamespace
from app import main
from test_match_windows import match

class FakeResponse:
    def raise_for_status(self): pass
    def json(self): return {'matches':[match(1,'2026-02-01',1,2),match(2,'2026-01-01',3,4)]}

class FakeClient:
    async def get(self,*args,**kwargs): return FakeResponse()

def test_coverage_marks_partial_and_provenance(monkeypatch):
    monkeypatch.setenv('FOOTBALL_DATA_API_KEY','test-token')
    monkeypatch.setattr(main.app.state,'client',FakeClient(),raising=False)
    r=asyncio.run(main.recent_matches(1,13,'all'))
    assert r['selectedCount']==1 and r['coverage']['ratio']==round(1/13,4)
    assert r['coverage']['providerReturned']==2
    assert r['coverage']['complete'] is False
    assert r['coverage']['source']=='football-data.org'
    assert 'does not prove' in r['coverageNote']

def test_coverage_complete(monkeypatch):
    monkeypatch.setenv('FOOTBALL_DATA_API_KEY','test-token')
    monkeypatch.setattr(main.app.state,'client',FakeClient(),raising=False)
    r=asyncio.run(main.recent_matches(1,1,'all'))
    assert r['coverage']['complete'] is True
    assert r['coverage']['ratio']==1
    assert r['coverageNote'] is None

def test_comparison_coverage_unequal(monkeypatch):
    async def fake(team_id,limit,venue):
        return {'teamId':team_id,'selectedCount':limit if team_id==1 else 3,'requestedCount':limit,'matches':[]}
    monkeypatch.setattr(main,'recent_matches',fake)
    r=asyncio.run(main.independent_match_windows(1,2,13,47,'all','all'))
    assert r['coverage']=={'ownComplete':True,'opponentComplete':False,'bothComplete':False}
