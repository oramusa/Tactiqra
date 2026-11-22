import {useEffect,useMemo,useState} from 'react';

type Shot={event_id:string|null;index:number;minute:number|null;second:number|null;period:number|null;team:string|null;team_id:number|null;player:string|null;location:number[]|null;outcome:string|null;statsbomb_xg:number|null};
type ShotResponse={status:string;reason?:string;shot_count?:number;located_count?:number;items:Shot[];notes?:string};
export default function HistoricalShotMap(){
 const [report,setReport]=useState<ShotResponse|null>(null);
 const [error,setError]=useState('');
 const [team,setTeam]=useState('all');
 const [outcome,setOutcome]=useState('all');
 const [selected,setSelected]=useState<string|null>(null);
 useEffect(()=>{const c=new AbortController();fetch('/api/v1/event-explorer/shots',{signal:c.signal}).then(r=>{if(!r.ok)throw Error('Shot API unavailable ('+r.status+')');return r.json()}).then(setReport).catch(e=>{if(e.name!=='AbortError')setError(String(e))});return()=>c.abort()},[]);
 const teams=useMemo(()=>Array.from(new Set((report?.items||[]).map(s=>s.team).filter((x):x is string=>!!x))),[report]);
 const outcomes=useMemo(()=>Array.from(new Set((report?.items||[]).map(s=>s.outcome).filter((x):x is string=>!!x))),[report]);
 const shots=(report?.items||[]).filter(s=>(team==='all'||s.team===team)&&(outcome==='all'||s.outcome===outcome));
 const active=shots.find(s=>String(s.index)===selected);
 const teamColor=(name:string|null)=>name===teams[0]?'#F7A65C':'#58D7CE';
 const fmt=(v:number|null)=>typeof v==='number'?v.toFixed(3):'—';
 return <section className="tq-shotmap">
 <style>{`
 .tq-shotmap{margin-top:24px;padding:22px;background:#101e30;border:1px solid #294158;border-radius:18px;color:#edf5fb}
 .tq-shotmap h3{margin:0 0 8px;font-size:21px}.tq-shotmap p{color:#aebfcf;font-size:13px}
 .tq-shot-controls{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}
 .tq-shot-controls label{display:flex;flex-direction:column;gap:7px;font-size:12px;color:#aebfcf}
 .tq-shot-controls select{padding:10px;background:#192d42;border:1px solid #3b576c;border-radius:9px;color:#fff}
 .tq-shot-summary{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0 18px}.tq-shot-summary span{padding:12px 16px;background:#1b3046;border:1px solid #31495e;border-radius:10px}
 .tq-shot-summary strong{font-size:22px;margin-right:6px}
 .tq-shot-pitch{display:block;width:100%;max-width:860px;margin:0 auto;border-radius:12px}
 .tq-shot-legend{display:flex;gap:16px;flex-wrap:wrap;justify-content:center;margin:14px 0;color:#c4d4df;font-size:13px}
 .tq-shot-legend i{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:7px}
 .tq-shot-detail{padding:14px;background:#1b3046;border-radius:10px;margin:14px 0;font-size:14px}
 .tq-shot-detail small{display:block;color:#aabccc;margin-top:7px}
 .tq-shot-list{max-height:260px;overflow:auto}.tq-shot-list button{display:block;width:100%;text-align:left;padding:10px 12px;background:transparent;border:0;border-bottom:1px solid #294158;color:#d8e6ef;cursor:pointer}.tq-shot-list button:hover,.tq-shot-list button[aria-pressed=true]{background:#25445a}
 `}</style>
 <h3>Shot Map · Tarihsel maç</h3>
 <p>Kaynak StatsBomb şut olayları · Hücum yönü doğrulanmadı · Resmî skorla eşleştirilmedi</p>
 {error&&<p role="alert">{error}</p>}
 {!report&&!error&&<p role="status">Şut verileri yükleniyor…</p>}
 {report?.status==='insufficient_data'&&<p role="status">{report.reason||'Veri bulunamadı'}</p>}
 {report?.status==='ready'&&<>
 <div className="tq-shot-summary"><span><strong>{report.shot_count??report.items.length}</strong>Kaynak şut olayı</span><span><strong>{report.located_count??0}</strong>Konumlu şut</span><span><strong>{shots.length}</strong>Filtrelenmiş şut</span></div>
 <div className="tq-shot-controls"><label>Takım<select value={team} onChange={e=>{setTeam(e.target.value);setSelected(null)}}><option value="all">İki takım</option>{teams.map(t=><option key={t}>{t}</option>)}</select></label><label>Şut sonucu<select value={outcome} onChange={e=>{setOutcome(e.target.value);setSelected(null)}}><option value="all">Tüm sonuçlar</option>{outcomes.map(o=><option key={o}>{o}</option>)}</select></label></div>
 <div className="tq-shot-legend">{teams.map(t=><span key={t}><i style={{background:teamColor(t)}}/>{t}</span>)}<span>◎ Gol sonucu (kaynak etiketi)</span></div>
 <svg className="tq-shot-pitch" viewBox="0 0 640 430" role="img" aria-label="Kaynak koordinatlarıyla gerçek şut olayları">
 <rect width="640" height="430" rx="12" fill="#15473e"/>
 {Array.from({length:10},(_,i)=><rect key={i} x={20+i*60} y="20" width="60" height="390" fill={i%2?'#fff':'#000'} opacity=".035"/>)}
 <g fill="none" stroke="#d5f0e6" strokeWidth="1.6" opacity=".85" pointerEvents="none"><rect x="20" y="20" width="600" height="390"/><path d="M320 20V410"/><circle cx="320" cy="215" r="64"/><rect x="20" y="115" width="102" height="200"/><rect x="20" y="161" width="38" height="108"/><rect x="518" y="115" width="102" height="200"/><rect x="582" y="161" width="38" height="108"/></g>
 {shots.filter(s=>s.location).map(s=>{const x=20+(s.location![0]/120)*600,y=20+(s.location![1]/80)*390,goal=s.outcome==='Goal',chosen=String(s.index)===selected;return <g key={s.event_id||s.index} role="button" tabIndex={0} aria-label={(s.player||'Oyuncu bilinmiyor')+' '+(s.minute??'?')+' dakika '+(s.outcome||'Sonuç bilinmiyor')} onClick={()=>setSelected(String(s.index))} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setSelected(String(s.index))}}} style={{cursor:'pointer'}}><circle cx={x} cy={y} r={chosen?12:goal?9:7} fill={teamColor(s.team)} stroke={chosen?'#fff':goal?'#fff':'#102e35'} strokeWidth={chosen?3:2} opacity=".94"/>{goal&&<circle cx={x} cy={y} r="3" fill="#102e35"/>}<title>{s.team||'—'} · {s.player||'—'} · {s.minute??'?'}' · {s.outcome||'—'}</title></g>})}
 </svg>
 {active&&<div className="tq-shot-detail" role="status"><strong>{active.player||'Oyuncu belirtilmemiş'}</strong> · {active.team||'Takım bilinmiyor'} · {active.minute??'?'}:{String(active.second??0).padStart(2,'0')} · {active.outcome||'Sonuç belirtilmemiş'}<small>Kaynak xG: {fmt(active.statsbomb_xg)} · Olay ID: {active.event_id||'—'} · Konum: {active.location?.join(', ')||'Yok'}</small></div>}
 <details><summary>Şut olayları ({shots.length})</summary><div className="tq-shot-list">{shots.map(s=><button key={s.index} type="button" aria-pressed={String(s.index)===selected} onClick={()=>setSelected(String(s.index))}>{s.minute??'?'}' · {s.team||'—'} · {s.player||'—'} · {s.outcome||'—'}{!s.location?' · Konum eksik':''}</button>)}</div></details>
 <p>{report.notes} Veriler yalnızca yerel tarihsel pilot dosyasından gelir; ticari kullanım izni doğrulanmadı.</p>
 </>}
 </section>;
}
