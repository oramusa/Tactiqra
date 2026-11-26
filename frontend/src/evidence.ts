export type EvidenceMatch = {
  matchId: number;
  source: string;
  eventIds: string[];
};
export type TacticalEvidence = {
  version: 1;
  module: 'OpponentIQ' | 'MatchIQ';
  provider: 'StatsBomb' | 'football-data.org';
  scope: string;
  title: string;
  observation: string;
  recommendation?: string;
  coverage: { matched: number; eligible: number; analyzed: number };
  matches: EvidenceMatch[];
  limitations: string[];
};
export function evidenceKey(e: TacticalEvidence): string {
  return JSON.stringify([e.module,e.provider,e.scope,e.title,e.coverage,
    e.matches.map(m=>[m.matchId,m.source,[...new Set(m.eventIds)].sort()]).sort((a,b)=>Number(a[0])-Number(b[0]))]);
}
export function evidenceText(e: TacticalEvidence): string {
  return [e.module,e.provider,e.scope,e.title,e.observation,e.recommendation,
    'Coverage '+e.coverage.matched+'/'+e.coverage.eligible+' eligible; '+e.coverage.analyzed+' analyzed',
    ...e.matches.map(m=>'Match '+m.matchId+' | '+m.source+' | event IDs '+m.eventIds.join(', ')),
    ...e.limitations].filter(Boolean).join(' · ');
}

export function isTacticalEvidence(value:unknown):value is TacticalEvidence {
  if(!value||typeof value!=='object')return false;
  const e=value as TacticalEvidence;
  const nonblank=(v:unknown):v is string=>typeof v==='string'&&v.trim().length>0;
  const count=(v:unknown):v is number=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=0;
  if(e.version!==1||!['OpponentIQ','MatchIQ'].includes(e.module)||!['StatsBomb','football-data.org'].includes(e.provider)||![e.scope,e.title,e.observation].every(nonblank)|| (e.recommendation!==undefined&&!nonblank(e.recommendation)))return false;
  const c=e.coverage;
  if(!c||![c.matched,c.eligible,c.analyzed].every(count)||c.matched>c.eligible||c.eligible>c.analyzed)return false;
  if(!Array.isArray(e.limitations)||!e.limitations.every(nonblank)||!Array.isArray(e.matches)||!e.matches.length)return false;
  const ids=new Set<number>();
  for(const m of e.matches){
    if(!m||!count(m.matchId)||m.matchId===0||ids.has(m.matchId)||!nonblank(m.source)||!Array.isArray(m.eventIds)||!m.eventIds.every(nonblank))return false;
    ids.add(m.matchId);
    if(e.provider==='StatsBomb'&&m.source!=='https://raw.githubusercontent.com/statsbomb/open-data/master/data/events/'+m.matchId+'.json')return false;
    if(e.provider==='football-data.org'){try{const u=new URL(m.source);if(u.protocol!=='https:'||!['api.football-data.org','www.football-data.org','football-data.org'].includes(u.hostname))return false}catch{return false}}
  }
  return true;
}
