import React,{useEffect,useState} from 'react';
type Team={team_id:number;team_name:string;event_count:number;passes:number;completed_passes:number;pass_completion_pct:number|null;shots:number;goals_from_shots:number;located_events:number};
type Report={status:string;teams:Team[];total_events?:number;skipped_events?:number;match_identity_verified:boolean;reason?:string;limitations?:string[]};
export default function HistoricalEventReport(){
 const [report,setReport]=useState<Report|null>(null),[error,setError]=useState('');
 const refresh=()=>{setError('');fetch('/api/v1/opponentiq/historical-event-report').then(async r=>{if(!r.ok)throw Error('Historical report API unavailable');return r.json()}).then(setReport).catch(e=>setError(e.message))};
 useEffect(()=>{refresh()},[]);
 return <section className="event-report"><div className="section-head"><div><div className="eyebrow">LOCAL EVENT DATA</div><h3>Historical Match Event Report</h3></div><button type="button" onClick={refresh}>Yenile</button></div>
 <p>Yalnızca bağlı tarihsel olay dosyasından hesaplanır. Yukarıdaki seçili takımın güncel maçlarıyla otomatik eşleşmez.</p>
 {error&&<p role="alert">{error}</p>}
 {!report&&!error&&<p>Rapor yükleniyor…</p>}
 {report?.status==='not_configured'&&<p role="status">Veri dosyası bağlı değil. {report.reason}</p>}
 {report?.status==='insufficient_data'&&<p role="status">Hesaplanabilir takım olayları yok.</p>}
 {report?.status==='event_summary'&&<><p role="status">{report.total_events} kayıt · {report.skipped_events} atlanan · Maç kimliği bağımsız doğrulanmadı</p><div className="event-report-grid">{report.teams.map(t=><article className="event-report-card" key={t.team_id}><h4>{t.team_name}</h4><dl><dt>Olaylar</dt><dd>{t.event_count}</dd><dt>Paslar</dt><dd>{t.passes}</dd><dt>Başarılı paslar</dt><dd>{t.completed_passes}</dd><dt>Pas isabeti</dt><dd>{t.pass_completion_pct===null?'—':`${t.pass_completion_pct}%`}</dd><dt>Şut olayları</dt><dd>{t.shots}</dd><dt>Gol sonuçlu şut</dt><dd>{t.goals_from_shots}</dd><dt>Konumlu olaylar</dt><dd>{t.located_events}</dd></dl></article>)}</div></>}
 <p className="heatmap-note">Olay sayıları topa sahip olma veya oyuncu tracking verisi değildir. Gol sonuçlu şut sayısı resmi skorla aynı olmak zorunda değildir. Kaynak dosyası ve maç kimliği ayrıca doğrulanmalıdır.</p>
 </section>;
}
