import React,{useEffect,useState} from 'react';
type Fixture={match_id:number;date:string;home:string;away:string};
type Side={shots:number;goals_from_shots:number;xg_sum:number|null;xg_count:number;box_shots:number;located_shots:number};
type Shot={event_id:string;side:'home'|'away';location:[number,number]|null;xg:number|null;player:string|null;minute:number|null;outcome:string|null};
type HeatRow={player_id:number|null;player:string;events:number;located:number;cells:number[]};
type PassNetwork={attempts:number;completed:number;mapped:number;nodes:{id:number;name:string|null;x:number|null;y:number|null;located:number}[];links:{from:number;to:number;count:number;event_ids:string[]}[]};
type Report=Fixture&{home_stats:Side;away_stats:Side;shots?:Shot[];pass_networks?:{home:PassNetwork;away:PassNetwork};heatmap?:{home:HeatRow[];away:HeatRow[]};source:string;limitations:string[]};
async function get(url:string,signal:AbortSignal){const r=await fetch(url,{signal});if(!r.ok)throw new Error('API '+r.status);return r.json()}
function ShotPitch({name,shots}:{name:string;shots:Shot[]}){
 const [selected,setSelected]=useState<string|null>(null);
 const located=shots.filter(s=>s.location!==null);
 const active=shots.find(s=>s.event_id===selected);
 return <div style={{minWidth:0}}><h3>{name}</h3><p>{located.length}/{shots.length} konumlu şut</p><svg viewBox="0 0 120 80" width="100%" role="img" aria-label={name+' şut haritası'} style={{background:'#153c30',borderRadius:6}}>
 <g fill="none" stroke="#a9c6b4" strokeWidth=".35"><rect x="1" y="1" width="118" height="78"/><path d="M60 1V79"/><circle cx="60" cy="40" r="9.15"/><rect x="1" y="18" width="17" height="44"/><rect x="102" y="18" width="17" height="44"/><rect x="1" y="30" width="5" height="20"/><rect x="114" y="30" width="5" height="20"/></g>
 {located.map(s=><circle key={s.event_id} cx={s.location![0]} cy={s.location![1]} r={1.4+3*Math.sqrt(s.xg??0)} fill={s.outcome==='Goal'?'#facc15':'#60a5fa'} fillOpacity=".78" stroke={selected===s.event_id?'white':'#172b24'} strokeWidth=".45" onClick={()=>setSelected(s.event_id)} style={{cursor:'pointer'}}><title>{s.player??'Unknown'} · {s.minute??'—'}′ · {s.outcome??'—'} · xG {s.xg?.toFixed(3)??'—'}</title></circle>)}</svg>
 <label>Şut kanıtı <select value={selected??''} onChange={e=>setSelected(e.target.value||null)}><option value="">Şut seçiniz</option>{shots.map(s=><option key={s.event_id} value={s.event_id}>{s.minute??'—'}′ · {s.player??'—'} · {s.outcome??'—'}</option>)}</select></label>
 {active&&<p style={{overflowWrap:'anywhere'}}>{active.player??'—'} · xG {active.xg?.toFixed(3)??'—'}<br/>Event ID: {active.event_id}</p>}</div>
}
function EventHeatmap({name,rows,max}:{name:string;rows:HeatRow[];max:number}){
 const [player,setPlayer]=useState('all');
 const chosen=player==='all'?rows:rows.filter(r=>String(r.player_id)===player);
 const cells=Array.from({length:96},(_,i)=>chosen.reduce((n,r)=>n+(r.cells[i]??0),0));
 const events=chosen.reduce((n,r)=>n+r.events,0),located=chosen.reduce((n,r)=>n+r.located,0);
 return <div style={{minWidth:0}}><h3>{name}</h3><label>Oyuncu <select value={player} onChange={e=>setPlayer(e.target.value)}><option value="all">Tüm takım</option>{rows.filter(r=>r.player_id!==null).map(r=><option key={r.player_id} value={String(r.player_id)}>{r.player}</option>)}</select></label><p>{located}/{events} konumlu olay</p>
 <svg viewBox="0 0 120 80" width="100%" role="img" aria-label={name+' olay yoğunluğu haritası'} style={{background:'#153c30',borderRadius:6}}>
 {Array.from({length:2400},(_,i)=>{const x=(i%60)*2+1,y=Math.floor(i/60)*2+1;let sum=0,weight=0;for(let j=0;j<96;j++){const dx=x-(j%12*10+5),dy=y-(Math.floor(j/12)*10+5),w=Math.exp(-(dx*dx+dy*dy)/65);sum+=cells[j]*w;weight+=w}const v=Math.min(1,sum/Math.max(weight,1e-9)/Math.max(1,max));const hue=120*(1-Math.sqrt(v));return <rect key={i} x={x-1} y={y-1} width="2.05" height="2.05" fill={`hsl(${hue},95%,48%)`} fillOpacity={Math.min(.95,v*1.5)}/>})}
 <g fill="none" stroke="#c6ded0" strokeWidth=".35" pointerEvents="none"><rect x=".5" y=".5" width="119" height="79"/><path d="M60 0V80"/><circle cx="60" cy="40" r="9.15"/><rect x=".5" y="18" width="17.5" height="44"/><rect x="102" y="18" width="17.5" height="44"/><rect x=".5" y="30" width="5.5" height="20"/><rect x="114" y="30" width="5.5" height="20"/></g></svg><div style={{height:8,borderRadius:4,background:"linear-gradient(90deg,#153c30,#49a52a,#e7db18,#f88a12,#e52222)"}}/><p>0 – {max} olay/hücre · En yoğun kaynak hücre: {Math.max(...cells)} olay</p></div>
}
function MatchHeatmaps({report}:{report:Report}){
 const h=report.heatmap;
 if(!h||!Array.isArray(h.home)||!Array.isArray(h.away))return <p>Isı haritası verisi henüz mevcut değil.</p>;
 const max=Math.max(1,...[h.home,h.away].flatMap(rows=>Array.from({length:96},(_,i)=>rows.reduce((n,r)=>n+(r.cells[i]??0),0))));
 return <><h3>Dynamic Player & Team Heatmaps</h3><p>12 × 8 kaynak hücreden yumuşatılmış olay yoğunluğu; ortak ölçek (0–{max} olay/hücre). Oyuncu filtresi ölçeği değiştirmez. Ham olay koordinatları; tracking veya sahada geçirilen süre değildir.</p><div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,280px),1fr))',gap:16}}><EventHeatmap key={report.match_id+'home'} name={report.home} rows={h.home} max={max}/><EventHeatmap key={report.match_id+'away'} name={report.away} rows={h.away} max={max}/></div></>
}
function PassPitch({name,network}:{name:string;network:PassNetwork}){
 const [threshold,setThreshold]=useState(5),[selected,setSelected]=useState('');
 const nodes=network.nodes.filter(n=>n.x!==null&&n.y!==null);
 const byId=new Map(nodes.map(n=>[n.id,n]));
 const links=network.links.filter(l=>l.count>=threshold&&byId.has(l.from)&&byId.has(l.to));
 const max=Math.max(1,...network.links.map(l=>l.count));
 const active=network.links.find(l=>l.from+'-'+l.to===selected);
 const nameOf=(id:number)=>network.nodes.find(n=>n.id===id)?.name??String(id);
 return <div style={{minWidth:0}}><h3>{name}</h3><p>{network.completed}/{network.attempts} başarılı pas · {network.mapped} kimliği eşleşen</p><label>Minimum pas: {threshold} <input type="range" min="1" max={Math.max(5,max)} value={threshold} onChange={e=>setThreshold(Number(e.target.value))}/></label>
 <svg viewBox="0 0 120 80" width="100%" role="img" aria-label={name+' pas ağı'} style={{background:'#153c30',borderRadius:6}}>
 <g fill="none" stroke="#a9c6b4" strokeWidth=".35"><rect x=".5" y=".5" width="119" height="79"/><path d="M60 0V80"/><circle cx="60" cy="40" r="9.15"/><rect x=".5" y="18" width="17.5" height="44"/><rect x="102" y="18" width="17.5" height="44"/></g>
 {links.map(l=>{const a=byId.get(l.from)!,b=byId.get(l.to)!;return <line key={l.from+'-'+l.to} x1={a.x!} y1={a.y!} x2={b.x!} y2={b.y!} stroke={selected===l.from+'-'+l.to?'#facc15':'#7dd3fc'} strokeWidth={.35+2.5*l.count/max} opacity=".8"><title>{nameOf(l.from)} → {nameOf(l.to)}: {l.count}</title></line>})}
 {nodes.map(n=><g key={n.id}><circle cx={n.x!} cy={n.y!} r="2" fill="#facc15" stroke="#132b24" strokeWidth=".4"/><text x={n.x!} y={n.y!-3} fontSize="2.6" textAnchor="middle" fill="white" stroke="#153c30" strokeWidth=".6" paintOrder="stroke">{(n.name??String(n.id)).split(' ').slice(-1)[0]}</text></g>)}</svg>
 <p>{nodes.length}/{network.nodes.length} konumlu oyuncu · {links.length} görünür yönlü bağlantı</p>
 <label>Pas bağlantısı <select value={selected} onChange={e=>setSelected(e.target.value)}><option value="">Bağlantı seç</option>{network.links.map(l=><option key={l.from+'-'+l.to} value={l.from+'-'+l.to}>{nameOf(l.from)} → {nameOf(l.to)} ({l.count})</option>)}</select></label>
 {active&&<details><summary>{active.count} başarılı pas · Kaynak Event ID</summary><div style={{overflowWrap:'anywhere',maxHeight:180,overflow:'auto'}}>{active.event_ids.map((id,i)=><div key={id+'-'+i}>{id}</div>)}</div></details>}</div>
}
function MatchPassNetworks({report}:{report:Report}){
 const n=report.pass_networks;
 if(!n)return <p>Pas ağı verisi henüz mevcut değil.</p>;
 return <><h3>Dynamic Pass Networks</h3><p>Başarılı pas başlangıçlarının ortalama konumları. Tüm maç ve oyuncu değişiklikleri birlikte; gerçek diziliş değildir. Çizgiler yönlü bağlantıların sayısını gösterir, karşılıklı bağlantılar üst üste gelebilir. Ölçek takım bazlıdır.</p><div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,280px),1fr))',gap:16}}><PassPitch key={report.match_id+'home'} name={report.home} network={n.home}/><PassPitch key={report.match_id+'away'} name={report.away} network={n.away}/></div></>
}
export default function DynamicMatchSelector(){
 const [matches,setMatches]=useState<Fixture[]>([]),[id,setId]=useState(''),[report,setReport]=useState<Report|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(false),[catalogLoading,setCatalogLoading]=useState(true);
 useEffect(()=>{const c=new AbortController();get('/api/v1/opponentiq/historical-match-catalog',c.signal).then(d=>{if(d.status!=='ready'||!Array.isArray(d.matches))throw new Error('Maç kataloğu hazır değil');setMatches(d.matches)}).catch(e=>{if(!c.signal.aborted)setError(e.message)}).finally(()=>{if(!c.signal.aborted)setCatalogLoading(false)});return()=>c.abort()},[]);
 useEffect(()=>{if(!id)return;const c=new AbortController();setReport(null);setError('');setLoading(true);get('/api/v1/opponentiq/historical-match/'+id,c.signal).then(d=>{if(String(d.match_id)!==id||!d.home_stats||!d.away_stats)throw new Error('Maç kimliği veya veri geçersiz');if(!c.signal.aborted)setReport(d)}).catch(e=>{if(!c.signal.aborted)setError(e.message)}).finally(()=>{if(!c.signal.aborted)setLoading(false)});return()=>c.abort()},[id]);
 const xg=(s:Side)=>s.xg_count===s.shots&&s.xg_sum!==null?s.xg_sum.toFixed(2):'—';
 return <section className="panel"><h2>Dynamic Match Selector</h2><p>StatsBomb · LaLiga 2020/21 · mevcut tarihsel maçlar</p><label htmlFor="historical-match">Maç seç</label><select id="historical-match" value={id} disabled={catalogLoading} onChange={e=>{setReport(null);setError('');setId(e.target.value);setLoading(!!e.target.value)}}><option value="">{catalogLoading?'Katalog yükleniyor…':'Maç seçiniz'}</option>{matches.map(m=><option key={m.match_id} value={m.match_id}>{m.date} · {m.home} – {m.away}</option>)}</select><p>{matches.length} mevcut maç</p>{error&&<p role="alert">{error}</p>}{loading&&<p role="status">Maç analiz ediliyor…</p>}{report&&String(report.match_id)===id&&<><h3>{report.home} – {report.away}</h3><p>{report.date} · #{report.match_id}</p><div className="metrics">{[['Şut golleri',report.home_stats.goals_from_shots+' / '+report.away_stats.goals_from_shots],['Şutlar',report.home_stats.shots+' / '+report.away_stats.shots],['xG',xg(report.home_stats)+' / '+xg(report.away_stats)],['Ceza sahası şutları',report.home_stats.box_shots+' / '+report.away_stats.box_shots]].map(([label,value])=><div className="metric" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>{Array.isArray(report.shots)?<><h3>Dynamic Shot Maps</h3><p>● Mavi: diğer şutlar · Sarı: gol · Boyut: xG (eksikse minimum). Ham StatsBomb koordinatları; yön bağımsız doğrulanmadı.</p><div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,280px),1fr))',gap:16}}><ShotPitch key={id+'home'} name={report.home} shots={report.shots.filter(s=>s.side==='home')}/><ShotPitch key={id+'away'} name={report.away} shots={report.shots.filter(s=>s.side==='away')}/></div></>:<p>Şut haritası verisi henüz mevcut değil.</p>}<MatchHeatmaps report={report}/><MatchPassNetworks report={report}/><a href={report.source} target="_blank" rel="noreferrer">StatsBomb kaynak olayları</a>{report.limitations.map(l=><p className="data-note" key={l}>{l}</p>)}</>}</section>
}
