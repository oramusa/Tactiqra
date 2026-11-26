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
