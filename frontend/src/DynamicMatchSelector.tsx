import React,{useEffect,useState} from 'react';
type Fixture={match_id:number;date:string;home:string;away:string};
type Side={shots:number;goals_from_shots:number;xg_sum:number|null;xg_count:number;box_shots:number;located_shots:number};
type Shot={event_id:string;side:'home'|'away';location:[number,number]|null;xg:number|null;player:string|null;minute:number|null;outcome:string|null};
type HeatRow={player_id:number|null;player:string;events:number;located:number;cells:number[]};
type PassNetwork={attempts:number;completed:number;mapped:number;nodes:{id:number;name:string|null;x:number|null;y:number|null;located:number}[];links:{from:number;to:number;count:number;event_ids:string[]}[]};
type TimelineEvent={event_id:string;side:'home'|'away';kind:string;detail:string|null;replacement:string|null;player:string|null;minute:number|null;second:number|null;period:number|null};
type PlayerRow={id:number;name:string|null;passes:number;completed:number;shots:number;goals:number;xg:number;xg_count:number;recoveries:number;pressures:number;loss_tags:number};
type Report=Fixture&{home_stats:Side;away_stats:Side;shots?:Shot[];players?:{home:PlayerRow[];away:PlayerRow[]};timeline?:TimelineEvent[];pass_networks?:{home:PassNetwork;away:PassNetwork};heatmap?:{home:HeatRow[];away:HeatRow[]};source:string;limitations:string[]};
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
function SmoothDensity({cells,max}:{cells:number[];max:number}){
 const ref=React.useRef<HTMLCanvasElement>(null);
 const key=cells.join(',');
 useEffect(()=>{
  const canvas=ref.current,ctx=canvas?.getContext('2d');if(!canvas||!ctx)return;
  const w=240,h=160,img=ctx.createImageData(w,h);
  const palette=[[21,60,48],[44,130,65],[225,220,28],[249,130,15],[230,34,34]];
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
   const gx=(x+.5)/2,gy=(y+.5)/2;let sum=0,weight=0;
   for(let j=0;j<96;j++){const dx=gx-(j%12*10+5),dy=gy-(Math.floor(j/12)*10+5),v=Math.exp(-(dx*dx+dy*dy)/65);sum+=cells[j]*v;weight+=v}
   const t=Math.min(1,Math.max(0,sum/Math.max(weight,1e-9)/Math.max(1,max))),p=t*4,k=Math.min(3,Math.floor(p)),f=p-k,i=(y*w+x)*4;
   for(let c=0;c<3;c++)img.data[i+c]=Math.round(palette[k][c]*(1-f)+palette[k+1][c]*f);
   img.data[i+3]=255;
  }
  ctx.putImageData(img,0,0);
 },[key,max]);
 return <canvas ref={ref} width={240} height={160} style={{display:'block',width:'120px',height:'80px'}} aria-hidden="true"/>;
}
function EventHeatmap({name,rows,max,auto}:{name:string;rows:HeatRow[];max:number;auto:boolean}){
 const [player,setPlayer]=useState('all');
 const chosen=player==='all'?rows:rows.filter(r=>String(r.player_id)===player);
 const cells=Array.from({length:96},(_,i)=>chosen.reduce((n,r)=>n+(r.cells[i]??0),0));
 const scale=auto?Math.max(1,...cells):max;
 const events=chosen.reduce((n,r)=>n+r.events,0),located=chosen.reduce((n,r)=>n+r.located,0);
 return <div style={{minWidth:0}}><h3>{name}</h3><label>Oyuncu <select value={player} onChange={e=>setPlayer(e.target.value)}><option value="all">Tüm takım</option>{rows.filter(r=>r.player_id!==null).map(r=><option key={r.player_id} value={String(r.player_id)}>{r.player}</option>)}</select></label><p>{located}/{events} konumlu olay</p>
 <svg viewBox="0 0 120 80" width="100%" role="img" aria-label={name+' olay yoğunluğu haritası'} style={{background:'#153c30',borderRadius:6}}>
 <foreignObject x="0" y="0" width="120" height="80"><SmoothDensity cells={cells} max={scale}/></foreignObject>
 <g fill="none" stroke="#c6ded0" strokeWidth=".35" pointerEvents="none"><rect x=".5" y=".5" width="119" height="79"/><path d="M60 0V80"/><circle cx="60" cy="40" r="9.15"/><rect x=".5" y="18" width="17.5" height="44"/><rect x="102" y="18" width="17.5" height="44"/><rect x=".5" y="30" width="5.5" height="20"/><rect x="114" y="30" width="5.5" height="20"/></g></svg><div style={{height:8,borderRadius:4,background:"linear-gradient(90deg,#153c30,#49a52a,#e7db18,#f88a12,#e52222)"}}/><p>{auto?'Auto':'Common'} · 0 – {scale} olay/hücre · En yoğun kaynak hücre: {Math.max(...cells)} olay</p></div>
}
function MatchHeatmaps({report}:{report:Report}){
 const [auto,setAuto]=useState(true);
 const h=report.heatmap;
 if(!h||!Array.isArray(h.home)||!Array.isArray(h.away))return <p>Isı haritası verisi henüz mevcut değil.</p>;
 const max=Math.max(1,...[h.home,h.away].flatMap(rows=>Array.from({length:96},(_,i)=>rows.reduce((n,r)=>n+(r.cells[i]??0),0))));
 return <><h3>Dynamic Player & Team Heatmaps</h3><p>12 × 8 kaynak hücreden yumuşatılmış olay yoğunluğu. Ham olay koordinatları; tracking veya sahada geçirilen süre değildir.</p><label>Renk ölçeği <select value={auto?'auto':'common'} onChange={e=>setAuto(e.target.value==='auto')}><option value="auto">Auto Scale — bağımsız</option><option value="common">Common Scale — ortak</option></select></label><p>{auto?'Renkler her seçimin kendi maksimumuna göre hesaplanır; renkler doğrudan karşılaştırılamaz.':'İki harita aynı takım bazlı maksimumu kullanır.'}</p><div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,280px),1fr))',gap:16}}><EventHeatmap auto={auto} key={report.match_id+'home'} name={report.home} rows={h.home} max={max}/><EventHeatmap auto={auto} key={report.match_id+'away'} name={report.away} rows={h.away} max={max}/></div></>
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
function MatchTimeline({report}:{report:Report}){
 const [kind,setKind]=useState('all'),[side,setSide]=useState('all');
 if(!Array.isArray(report.timeline))return <p>Maç akışı verisi henüz mevcut değil.</p>;
 const events=report.timeline.filter(e=>(side==='all'||side===e.side)&&(kind==='all'||(kind==='goals'?['Goal','Own Goal For','Own Goal Against'].includes(e.kind):kind===e.kind)));
 const labels:Record<string,string>={'Goal':'Gol','Shot':'Şut','Card':'Kart','Substitution':'Oyuncu değişikliği','Own Goal For':'Kendi kalesine gol (lehine)','Own Goal Against':'Kendi kalesine gol (aleyhine)'};
 return <section style={{marginTop:24}}><h3>Dynamic Match Timeline</h3><p>Kaynak olay sırası · Kendi kalesine gol kayıtları iki taraf için ayrı etiketlenebilir; bunları toplamayın.</p><div className="filters"><label>Olay <select value={kind} onChange={e=>setKind(e.target.value)}>{[['all','Tüm olaylar'],['goals','Goller'],['Shot','Gol olmayan şutlar'],['Card','Kartlar'],['Substitution','Değişiklikler']].map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label> <label>Takım <select value={side} onChange={e=>setSide(e.target.value)}><option value="all">İki takım</option><option value="home">{report.home}</option><option value="away">{report.away}</option></select></label></div><p>{events.length}/{report.timeline.length} kaynak olay</p><div style={{maxHeight:480,overflow:'auto'}}>{events.map((e,i)=><details key={e.event_id+'-'+i} style={{padding:'10px 8px',borderBottom:'1px solid #34464d'}}><summary style={{cursor:'pointer'}}><strong>{e.minute??'—'}:{e.second==null?'—':String(e.second).padStart(2,'0')}</strong> · {e.side==='home'?report.home:report.away} · {labels[e.kind]??e.kind} · {e.player??'—'}{e.replacement?' → '+e.replacement:''}{e.detail?' · '+e.detail:''}</summary><p style={{overflowWrap:'anywhere'}}>Period: {e.period??'—'} · Event ID: {e.event_id}</p></details>)}{!events.length&&<p>Bu filtrede kaynak olay yok.</p>}</div></section>
}
function PlayerPerformance({report}:{report:Report}){
 const [side,setSide]=useState<'home'|'away'>('home'),[sort,setSort]=useState<'passes'|'shots'|'goals'|'recoveries'|'pressures'>('passes');
 const [left,setLeft]=useState(''),[right,setRight]=useState('');
 if(!report.players)return <p>Oyuncu verisi henüz mevcut değil.</p>;
 const all=[...report.players.home.map(p=>({...p,key:'home:'+p.id,team:report.home})),...report.players.away.map(p=>({...p,key:'away:'+p.id,team:report.away}))];
 const rows=[...report.players[side]].sort((a,b)=>b[sort]-a[sort]);
 const metrics=(p:PlayerRow)=>[p.passes,p.completed,p.passes?(100*p.completed/p.passes).toFixed(1)+'%':'—',p.shots,p.goals,p.xg_count===p.shots?p.xg.toFixed(2):'—',p.recoveries,p.pressures,p.loss_tags];
 const labels=['Pas','Başarılı','Pas %','Şut','Gol','xG','Top kazanma','Pres olayı','Kayıp etiketi'];
 const a=all.find(p=>p.key===left),b=all.find(p=>p.key===right);
 return <section><h3>Player Performance Intelligence</h3><p>Kaynak olay sayıları; dakika başına normalizasyon, tracking ve oyuncu puanı değildir. Kayıp etiketi yalnızca Dispossessed/Miscontrol.</p><div className="filters"><label>Takım <select value={side} onChange={e=>setSide(e.target.value==='home'?'home':'away')}><option value="home">{report.home}</option><option value="away">{report.away}</option></select></label><label>Sırala <select value={sort} onChange={e=>setSort(e.target.value as typeof sort)}>{['passes','shots','goals','recoveries','pressures'].map(k=><option key={k}>{k}</option>)}</select></label></div><div style={{overflowX:'auto'}}><table><thead><tr><th>Oyuncu</th>{labels.map(l=><th key={l}>{l}</th>)}</tr></thead><tbody>{rows.map(p=><tr key={p.id}><td>{p.name??p.id}</td>{metrics(p).map((v,i)=><td key={i}>{v}</td>)}</tr>)}</tbody></table></div><h3>Player Comparison</h3><div className="filters">{[[left,setLeft],[right,setRight]].map(([v,set],i)=><label key={i}>Oyuncu {i+1} <select value={v as string} onChange={e=>(set as (v:string)=>void)(e.target.value)}><option value="">Seçiniz</option>{all.map(p=><option key={p.key} value={p.key}>{p.name??p.id} · {p.team}</option>)}</select></label>)}</div>{a&&b&&<table><thead><tr><th>Metrik</th><th>{a.name}</th><th>{b.name}</th></tr></thead><tbody>{labels.map((l,i)=><tr key={l}><td>{l}</td><td>{metrics(a)[i]}</td><td>{metrics(b)[i]}</td></tr>)}</tbody></table>}</section>
}
function AutomatedMatchReport({report,onCoachEvidence}:{report:Report;onCoachEvidence?:(e:string)=>void}){
 const a=report.home_stats,b=report.away_stats;
 const lines=[report.home+' – '+report.away+' | '+report.date+' | Match #'+report.match_id,
 'Şutlar: '+a.shots+' / '+b.shots,
 'Şut golleri: '+a.goals_from_shots+' / '+b.goals_from_shots,
 'Ceza sahası şutları (ham koordinatlar): '+a.box_shots+' / '+b.box_shots,
 a.shots===b.shots?'Şut sayıları eşit.':(a.shots>b.shots?report.home:report.away)+' daha fazla şut kaydetti.',
 a.xg_count===a.shots&&b.xg_count===b.shots&&a.xg_sum!==null&&b.xg_sum!==null?'Kaynak xG: '+a.xg_sum.toFixed(2)+' / '+b.xg_sum.toFixed(2):'xG karşılaştırması: veri eksik.',
 ...(report.pass_networks?['Başarılı paslar: '+report.pass_networks.home.completed+' / '+report.pass_networks.away.completed]:[]),
 'Sınırlamalar: '+report.limitations.join(' '),
 'Kaynak: '+report.source];
 const download=()=>{const url=URL.createObjectURL(new Blob([lines.join('\n')],{type:'text/plain;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download='tactiqra-match-'+report.match_id+'.txt';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
 return <section><h3>Automated Match Report</h3><p>Seçilen maçtan deterministik özet; taktik nedensellik veya gelecek performans tahmini değildir.</p>{lines.map((l,i)=><p key={i}>{l}</p>)}<button type="button" onClick={download}>Raporu indir (.txt)</button> {onCoachEvidence&&<button type="button" onClick={()=>onCoachEvidence(lines.join(' · '))}>Maç kanıtını CoachIQ'ya aktar</button>}</section>
}
export default function DynamicMatchSelector({onCoachEvidence}:{onCoachEvidence?:(e:string)=>void}={}){
 const [view,setView]=useState('Overview');
 const [matches,setMatches]=useState<Fixture[]>([]),[id,setId]=useState(''),[report,setReport]=useState<Report|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(false),[catalogLoading,setCatalogLoading]=useState(true);
 useEffect(()=>{const c=new AbortController();get('/api/v1/opponentiq/historical-match-catalog',c.signal).then(d=>{if(d.status!=='ready'||!Array.isArray(d.matches))throw new Error('Maç kataloğu hazır değil');setMatches(d.matches)}).catch(e=>{if(!c.signal.aborted)setError(e.message)}).finally(()=>{if(!c.signal.aborted)setCatalogLoading(false)});return()=>c.abort()},[]);
 useEffect(()=>{if(!id)return;const c=new AbortController();setReport(null);setError('');setLoading(true);get('/api/v1/opponentiq/historical-match/'+id,c.signal).then(d=>{if(String(d.match_id)!==id||!d.home_stats||!d.away_stats)throw new Error('Maç kimliği veya veri geçersiz');if(!c.signal.aborted)setReport(d)}).catch(e=>{if(!c.signal.aborted)setError(e.message)}).finally(()=>{if(!c.signal.aborted)setLoading(false)});return()=>c.abort()},[id]);
 const xg=(s:Side)=>s.xg_count===s.shots&&s.xg_sum!==null?s.xg_sum.toFixed(2):'—';
 return <section className="panel"><h2>Dynamic Match Selector</h2><p>StatsBomb · LaLiga 2020/21 · mevcut tarihsel maçlar</p><label htmlFor="historical-match">Maç seç</label><select id="historical-match" value={id} disabled={catalogLoading} onChange={e=>{setReport(null);setError('');setId(e.target.value);setLoading(!!e.target.value)}}><option value="">{catalogLoading?'Katalog yükleniyor…':'Maç seçiniz'}</option>{matches.map(m=><option key={m.match_id} value={m.match_id}>{m.date} · {m.home} – {m.away}</option>)}</select><p>{matches.length} mevcut maç</p>{error&&<p role="alert">{error}</p>}{loading&&<p role="status">Maç analiz ediliyor…</p>}{report&&String(report.match_id)===id&&<><h3>{report.home} – {report.away}</h3><p>{report.date} · #{report.match_id}</p><nav className="tabs" aria-label="Match analysis sections" style={{display:"flex",flexWrap:"wrap",gap:8,margin:"16px 0"}}>{["Overview","Shots","Heatmaps","Passes","Timeline","Players","Report"].map(v=><button type="button" key={v} aria-pressed={view===v} className={view===v?"active":""} onClick={()=>setView(v)}>{v}</button>)}</nav>{view==="Overview"&&<div className="metrics">{[['Şut golleri',report.home_stats.goals_from_shots+' / '+report.away_stats.goals_from_shots],['Şutlar',report.home_stats.shots+' / '+report.away_stats.shots],['xG',xg(report.home_stats)+' / '+xg(report.away_stats)],['Ceza sahası şutları',report.home_stats.box_shots+' / '+report.away_stats.box_shots]].map(([label,value])=><div className="metric" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>}{view==="Shots"&&(Array.isArray(report.shots)?<><h3>Dynamic Shot Maps</h3><p>● Mavi: diğer şutlar · Sarı: gol · Boyut: xG (eksikse minimum). Ham StatsBomb koordinatları; yön bağımsız doğrulanmadı.</p><div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,280px),1fr))',gap:16}}><ShotPitch key={id+'home'} name={report.home} shots={report.shots.filter(s=>s.side==='home')}/><ShotPitch key={id+'away'} name={report.away} shots={report.shots.filter(s=>s.side==='away')}/></div></>:<p>Şut haritası verisi henüz mevcut değil.</p>)}{view==="Heatmaps"&&<MatchHeatmaps report={report}/>} {view==="Passes"&&<MatchPassNetworks report={report}/>} {view==="Timeline"&&<MatchTimeline key={report.match_id} report={report}/>} {view==="Players"&&<PlayerPerformance key={report.match_id} report={report}/>} {view==="Report"&&<AutomatedMatchReport report={report} onCoachEvidence={onCoachEvidence}/>}<a href={report.source} target="_blank" rel="noreferrer">StatsBomb kaynak olayları</a>{report.limitations.map(l=><p className="data-note" key={l}>{l}</p>)}</>}</section>
}
