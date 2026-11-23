import {useEffect,useMemo,useState} from 'react';

type Shot={event_id:string|null;index:number;minute:number|null;second:number|null;period:number|null;team:string|null;team_id:number|null;player:string|null;location:number[]|null;outcome:string|null;shot_type?:string|null;statsbomb_xg:number|null};
type ShotResponse={status:string;reason?:string;shot_count?:number;located_count?:number;items:Shot[];notes?:string};
export default function HistoricalShotMap(){
 const [report,setReport]=useState<ShotResponse|null>(null);
 const [error,setError]=useState('');
 const [team,setTeam]=useState('all');
 const [outcome,setOutcome]=useState('all');
 const [selected,setSelected]=useState<string|null>(null);
 const [layout,setLayout]=useState<'split'|'combined'>('split');
 
 useEffect(()=>{const c=new AbortController();fetch('/api/v1/event-explorer/shots',{signal:c.signal}).then(r=>{if(!r.ok)throw Error('Shot API unavailable ('+r.status+')');return r.json()}).then(setReport).catch(e=>{if(e.name!=='AbortError')setError(String(e))});return()=>c.abort()},[]);
 const teams=useMemo(()=>Array.from(new Set((report?.items||[]).map(s=>s.team).filter((x):x is string=>!!x))),[report]);
 const outcomes=useMemo(()=>Array.from(new Set((report?.items||[]).map(s=>s.outcome).filter((x):x is string=>!!x))),[report]);
 const shots=(report?.items||[]).filter(s=>(team==='all'||s.team===team)&&(outcome==='all'||s.outcome===outcome));
 const allShots=report?.items||[];
 const xgTotal=(items:Shot[])=>items.reduce((sum,s)=>sum+(typeof s.statsbomb_xg==='number'&&Number.isFinite(s.statsbomb_xg)?s.statsbomb_xg:0),0);
 const xgCoverage=(items:Shot[])=>items.filter(s=>typeof s.statsbomb_xg==='number'&&Number.isFinite(s.statsbomb_xg)).length;
 const teamStats=teams.map(name=>{const items=allShots.filter(s=>s.team===name);const covered=xgCoverage(items);return {name,items,covered,goals:items.filter(s=>s.outcome==='Goal').length,total:xgTotal(items),complete:covered===items.length&&items.length>0};});
 const playerStats=Array.from(new Set(shots.map(s=>s.player).filter((p):p is string=>!!p))).map(name=>{const items=shots.filter(s=>s.player===name);const covered=xgCoverage(items);return {name,team:items[0]?.team||'—',count:items.length,goals:items.filter(s=>s.outcome==='Goal').length,covered,xg:xgTotal(items)};}).sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name));
 // StatsBomb 120x80 pitch; attacking penalty area is x>=102 and 18<=y<=62.
 // Coordinates are shot-oriented in this pilot; do not extrapolate to all event types.
 const zone=(shot:Shot):'inside'|'outside'|'unknown'=>{const p=shot.location;if(!p||!Number.isFinite(p[0])||!Number.isFinite(p[1]))return 'unknown';return p[0]>=102&&p[1]>=18&&p[1]<=62?'inside':'outside';};
 const zoneStats=teams.filter(name=>team==='all'||team===name).map(name=>{const items=shots.filter(s=>s.team===name);return {name,inside:items.filter(s=>zone(s)==='inside').length,outside:items.filter(s=>zone(s)==='outside').length,unknown:items.filter(s=>zone(s)==='unknown').length};});
 const shotIsPenalty=(s:Shot)=>s.shot_type==='Penalty';
 const shotTypeKnown=(s:Shot)=>typeof s.shot_type==='string'&&s.shot_type.length>0;
 const opponentInsights=teamStats.map(t=>{const inside=t.items.filter(s=>zone(s)==='inside').length;const outside=t.items.filter(s=>zone(s)==='outside').length;const unknown=t.items.length-inside-outside;return {name:t.name,shots:t.items.length,inside,outside,unknown,goals:t.goals,complete:t.complete,total:t.total,coverage:t.covered,penalties:t.items.filter(shotIsPenalty).length,unknownTypes:t.items.filter(s=>!shotTypeKnown(s)).length,nonPenalty:t.items.filter(s=>shotTypeKnown(s)&&!shotIsPenalty(s)),penaltyItems:t.items.filter(shotIsPenalty)};});
 const concentrationFindings=teamStats.map(t=>{
  const eligible=t.items.filter(s=>typeof s.statsbomb_xg==='number'&&Number.isFinite(s.statsbomb_xg));
  if(!t.complete||t.total<=0||eligible.length===0)return null;
  const largest=eligible.reduce((a,b)=>(a.statsbomb_xg??0)>=(b.statsbomb_xg??0)?a:b);
  const share=(largest.statsbomb_xg??0)/t.total;
  return {name:t.name,share,largest,total:t.total,shots:t.items.length,flagged:share>=0.5};
 }).filter((x):x is NonNullable<typeof x>=>x!==null);
 const active=shots.find(s=>String(s.index)===selected);
 const teamColor=(name:string|null)=>name===teams[0]?'#F7A65C':'#58D7CE';
 const fmt=(v:number|null)=>typeof v==='number'?v.toFixed(3):'—';
 // StatsBomb standard pitch is 120 x 80 coordinate units. Metric conversion is approximate.
 // Do not infer attack direction from this assumption.
 const geometry=(s:Shot)=>{if(!s.location)return null;const [x,y]=s.location;const dx=(120-x)*105/120,dy=(y-40)*68/80;const post=7.32/2;
 const distance=Math.hypot(dx,dy);const angle=Math.abs(Math.atan2(post-dy,dx)-Math.atan2(-post-dy,dx))*180/Math.PI;
 return {distance,angle};};
 const selectShot=(shot:Shot)=>{setSelected(String(shot.index));};
 const renderPitch=(subset:Shot[],label:string)=>{const positioned=subset.filter(s=>s.location);const clusters=new Map<string,Shot[]>();positioned.forEach(s=>{const key=s.location!.map(n=>Math.round(n/2)).join(':');clusters.set(key,[...(clusters.get(key)||[]),s])});return <div className="tq-shot-field"><h4>{label} <small>· {subset.length} şut</small></h4><svg className="tq-shot-pitch" viewBox="0 0 640 430" role="group" aria-label={label+' şut konumları'}><rect width="640" height="430" rx="12" fill="#15473e"/>{Array.from({length:10},(_,i)=><rect key={i} x={20+i*60} y="20" width="60" height="390" fill={i%2?'#fff':'#000'} opacity=".035"/>)}<g fill="none" stroke="#d5f0e6" strokeWidth="1.6" opacity=".85" pointerEvents="none"><rect x="20" y="20" width="600" height="390"/><path d="M320 20V410"/><circle cx="320" cy="215" r="64"/><rect x="20" y="115" width="102" height="200"/><rect x="20" y="161" width="38" height="108"/><rect x="518" y="115" width="102" height="200"/><rect x="582" y="161" width="38" height="108"/></g>{Array.from(clusters.entries()).map(([key,group])=>{const x=20+group[0].location![0]/120*600,y=20+group[0].location![1]/80*390;const chosen=group.some(s=>String(s.index)===selected);const goal=group.some(s=>s.outcome==='Goal');const color=group.every(s=>s.team===group[0].team)?teamColor(group[0].team):'#e4e6ed';return <g key={key} role="button" tabIndex={0} aria-label={group.length+' şut, '+group.map(s=>(s.player||'Oyuncu bilinmiyor')+' '+(s.minute??'?')+' dakika').join('; ')} onClick={()=>{const current=group.findIndex(s=>String(s.index)===selected);selectShot(group[(current+1)%group.length])}} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();const current=group.findIndex(s=>String(s.index)===selected);selectShot(group[(current+1)%group.length])}}} style={{cursor:'pointer'}}><circle cx={x} cy={y} r={chosen?13:group.length>1?11:goal?9:7} fill={color} stroke={chosen?'#fff':goal?'#fff':'#102e35'} strokeWidth={chosen?3:2}/>{goal&&<circle cx={x} cy={y} r="3" fill="#102e35"/>}{group.length>1&&<text x={x} y={y+3.5} fontSize="10" textAnchor="middle" fontWeight="bold" fill="#092b30">{group.length}</text>}<title>{group.length} şut · Tekrar tıklayarak aynı bölgedeki şutlar arasında geçiş yapın</title></g>})}</svg></div>};
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
 .tq-shot-table{width:100%;border-collapse:collapse;font-size:13px;margin:10px 0}.tq-shot-table th,.tq-shot-table td{padding:9px;text-align:left;border-bottom:1px solid #355066}.tq-shot-table th{color:#aebfcf;font-weight:500}.tq-shot-table-wrap{overflow-x:auto}.tq-opponent-iq{margin:20px 0;padding:18px;background:#14283d;border:1px solid #3a6073;border-radius:14px}.tq-opponent-iq h3{font-size:19px;margin:0 0 8px}.tq-opponent-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;margin:14px 0}.tq-opponent-card{padding:15px;background:#1b3549;border:1px solid #39566b;border-radius:10px;min-width:0}.tq-opponent-card h4{margin:0 0 12px}.tq-opponent-card p{margin:8px 0}.tq-opponent-card small{color:#adc4d4;overflow-wrap:anywhere}.tq-opponent-card button{margin-top:12px;padding:9px 12px;background:#24536b;color:#edf5fb;border:1px solid #4b7c91;border-radius:8px;cursor:pointer}.tq-opponent-card button:disabled{opacity:.45;cursor:not-allowed}.tq-opponent-caution{border-top:1px solid #39566b;padding-top:12px}.tq-shot-xg{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:14px 0}.tq-shot-xg div{padding:12px;background:#192e43;border:1px solid #355066;border-radius:10px}.tq-shot-xg strong{display:block;font-size:21px}.tq-shot-xg small{color:#adc2d2}.tq-shot-layout{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.tq-shot-field{min-width:0}.tq-shot-field h4{font-size:15px;margin:4px 0 12px}.tq-shot-field h4 small{color:#aebfcf;font-weight:normal}.tq-shot-detail{border-left:3px solid #6dd5cd}.tq-shot-layout .tq-shot-pitch{max-width:none}@media(max-width:760px){.tq-shot-layout{grid-template-columns:1fr}} .tq-shot-list{max-height:260px;overflow:auto}.tq-shot-list button{display:block;width:100%;text-align:left;padding:10px 12px;background:transparent;border:0;border-bottom:1px solid #294158;color:#d8e6ef;cursor:pointer}.tq-shot-list button:hover,.tq-shot-list button[aria-pressed=true]{background:#25445a}
 `}</style>
 <h3>Shot Map · Tarihsel maç</h3>
 <p>Kaynak StatsBomb şut olayları · Hücum yönü doğrulanmadı · Resmî skorla eşleştirilmedi</p>
 {error&&<p role="alert">{error}</p>}
 {!report&&!error&&<p role="status">Şut verileri yükleniyor…</p>}
 {report?.status==='insufficient_data'&&<p role="status">{report.reason||'Veri bulunamadı'}</p>}
 {report?.status==='ready'&&<>
 <div className="tq-shot-summary"><span><strong>{report.shot_count??report.items.length}</strong>Kaynak şut olayı</span><span><strong>{report.located_count??0}</strong>Konumlu şut</span><span><strong>{shots.length}</strong>Filtrelenmiş şut</span></div>
 <div className="tq-shot-xg" aria-label="Kaynak xG özeti">{teams.filter(t=>team==='all'||team===t).map(t=>{const subset=shots.filter(s=>s.team===t);const covered=xgCoverage(subset);return <div key={t}><small>{t} · Kaynak xG toplamı</small><strong>{covered===subset.length?xgTotal(subset).toFixed(2):'Eksik'}</strong><small>{covered}/{subset.length} şut için xG · Seçili filtre</small></div>})}</div>
 <section className="tq-opponent-iq" aria-label="OpponentIQ V1 şut kalitesi analizi">
 <h3>OpponentIQ V1 · Shot Quality Intelligence</h3>
 <p>Tek maçlık, kaynak olaylarına bağlı karşılaştırma. Penaltı ayrımı StatsBomb shot.type alanına dayanır; tür eksikse penaltı hariç xG gösterilmez. Bu bölüm rakibin gelecekteki davranışını tahmin etmez.</p>
 <div className="tq-opponent-grid">{opponentInsights.map(t=><article key={t.name} className="tq-opponent-card"><h4>{t.name}</h4>
 <p><strong>{t.shots}</strong> kaynak şut · <strong>{t.goals}</strong> kaynak gol etiketi</p>
 <p>Ceza sahası içi: <strong>{t.inside}</strong> · Dışı: <strong>{t.outside}</strong>{t.unknown>0?' · Konumsuz: '+t.unknown:''}</p>
 <p>Kaynak xG: <strong>{t.complete?t.total.toFixed(2):'Eksik veri'}</strong> · Kapsam: {t.coverage}/{t.shots}</p>
 <p>Şut başına xG: <strong>{t.complete?(t.total/t.shots).toFixed(3):'—'}</strong></p>
 <p>Kaynak penaltı şutu: <strong>{t.penalties}</strong> · Türü bilinmeyen: <strong>{t.unknownTypes}</strong></p>
 <p>Penaltı hariç xG: <strong>{t.unknownTypes===0&&t.nonPenalty.length>0&&xgCoverage(t.nonPenalty)===t.nonPenalty.length?xgTotal(t.nonPenalty).toFixed(2):'Doğrulanamadı'}</strong> · {t.nonPenalty.length} penaltı dışı şut</p>
 <p>Penaltı xG: <strong>{t.penaltyItems.length>0&&xgCoverage(t.penaltyItems)===t.penaltyItems.length?xgTotal(t.penaltyItems).toFixed(2):t.penaltyItems.length===0&&t.unknownTypes===0?'0.00':'Doğrulanamadı'}</strong></p>
 <small>Kanıt: {t.shots} Shot olayı, {t.coverage} kaynak xG alanı. Şutlar ve gol etiketleri resmî skorla bağımsız doğrulanmadı.</small>
 </article>)}</div>
 <p className="tq-opponent-caution">Yorum sınırı: Şut sayısı ve xG yalnızca bu maçın gözlemidir. Hücum yönü tüm olay türleri için doğrulanmadı. Çok maçlı rakip eğilimi ve otomatik taktik önerisi henüz etkin değildir.</p>
 </section>
 <section className="tq-opponent-iq" aria-label="OpponentIQ V1.2 kaynaklı xG yoğunlaşması">
 <h3>OpponentIQ V1.2 · xG Concentration Evidence</h3>
 <p>Bir takımın toplam kaynak xG'sinin en yüksek xG'li tek şutta ne kadar yoğunlaştığını gösterir. Eşik: %50; bu bir araştırma uyarısıdır, takım gücü puanı değildir.</p>
 {concentrationFindings.length===0?<p>Güvenilir hesap için tüm şutlarda kaynak xG bulunmalı ve toplam xG sıfırdan büyük olmalı.</p>:<div className="tq-opponent-grid">{concentrationFindings.map(f=><article key={f.name} className="tq-opponent-card">
 <h4>{f.name}</h4>
 <p><strong>{(f.share*100).toFixed(1)}%</strong> · en yüksek tek şutun toplam xG payı</p>
 <p>En yüksek şut xG: <strong>{(f.largest.statsbomb_xg??0).toFixed(3)}</strong> / {f.total.toFixed(3)} toplam xG</p>
 <p>{f.flagged?'Dikkat: xG tek pozisyonda yoğunlaşıyor.':'Bu maçta %50 yoğunlaşma eşiği aşılmadı.'}</p>
 <small>Kanıt: {f.largest.player||'Oyuncu bilinmiyor'} · {f.largest.minute??'?'}' · {f.largest.shot_type||'Tür bilinmiyor'} · {f.shots} şutluk örneklem · Olay ID: {f.largest.event_id||'Yok'}</small>
 <div><button type="button" disabled={!shots.some(s=>s.index===f.largest.index)} onClick={()=>{setSelected(String(f.largest.index));document.getElementById('tq-selected-shot')?.scrollIntoView({behavior:'smooth',block:'center'});}}>Şut detayını göster</button></div>
 </article>)}</div>}
 <p className="tq-opponent-caution">Kaynak xG yeniden hesaplanmaz. Tek maç ve küçük şut örneklemi nedeniyle bu bulgu gelecekteki rakip davranışını kanıtlamaz.</p>
 </section>
 <h4>Maç geneli · takım şut kalitesi</h4>
 <p>Bu tablo filtrelerden bağımsızdır. Gol sayısı yalnızca kaynak şut sonucu etiketlerinden sayılır; resmî skor doğrulaması değildir.</p>
 <div className="tq-shot-table-wrap"><table className="tq-shot-table"><thead><tr><th>Takım</th><th>Şut</th><th>Gol etiketi</th><th>Kaynak xG</th><th>xG / şut</th><th>xG kapsamı</th><th>Gol − xG</th></tr></thead><tbody>{teamStats.map(t=><tr key={t.name}><td>{t.name}</td><td>{t.items.length}</td><td>{t.goals}</td><td>{t.complete?t.total.toFixed(2):'Eksik'}</td><td>{t.complete?(t.total/t.items.length).toFixed(3):'—'}</td><td>{t.covered}/{t.items.length}</td><td>{t.complete?(t.goals-t.total).toFixed(2):'—'}</td></tr>)}</tbody></table></div>
 <div className="tq-shot-controls"><label>Takım<select value={team} onChange={e=>{setTeam(e.target.value);setSelected(null)}}><option value="all">İki takım</option>{teams.map(t=><option key={t}>{t}</option>)}</select></label><label>Şut sonucu<select value={outcome} onChange={e=>{setOutcome(e.target.value);setSelected(null)}}><option value="all">Tüm sonuçlar</option>{outcomes.map(o=><option key={o}>{o}</option>)}</select></label></div>
 <h4>Ceza sahası içi / dışı şut dağılımı</h4>
 <p>Seçili takım ve sonuç filtreleri uygulanır. Ceza sahası sınırı StatsBomb 120 × 80 koordinatları için x ≥ 102 ve 18 ≤ y ≤ 62 kabul edilir. Bu sınıflama kaynak koordinatına dayalıdır, bağımsız saha yönü doğrulaması değildir.</p>
 <div className="tq-shot-table-wrap"><table className="tq-shot-table"><thead><tr><th>Takım</th><th>İçeride</th><th>Dışarıda</th><th>Konumsuz</th></tr></thead><tbody>{zoneStats.map(z=><tr key={z.name}><td>{z.name}</td><td>{z.inside}</td><td>{z.outside}</td><td>{z.unknown}</td></tr>)}</tbody></table></div>
 <div className="tq-shot-legend">{teams.map(t=><span key={t}><i style={{background:teamColor(t)}}/>{t}</span>)}<span>◎ Gol sonucu (kaynak etiketi)</span></div>
 <div className="tq-shot-controls"><label>Görünüm<select value={layout} onChange={e=>{setLayout(e.target.value as 'split'|'combined');setSelected(null)}}><option value="split">Yan yana takım haritaları</option><option value="combined">Birleşik harita</option></select></label></div>
 <p>Yakın konumdaki şutlar tek noktada sayı ile gruplanır. Tekrar tıklayarak gruptaki şutlar arasında geçiş yapabilirsiniz. Kaynak koordinatları değiştirilmez.</p>
 <div className={layout==='split'?'tq-shot-layout':'tq-shot-layout tq-shot-layout-one'} style={layout==='combined'?{gridTemplateColumns:'1fr'}:undefined}>{layout==='split'?teams.filter(t=>team==='all'||team===t).map(t=><div key={t}>{renderPitch(shots.filter(s=>s.team===t),t)}</div>):renderPitch(shots,'İki takım · birleşik')}</div> {active&&<div id="tq-selected-shot" className="tq-shot-detail" role="status"><strong>{active.player||'Oyuncu belirtilmemiş'}</strong> · {active.team||'Takım bilinmiyor'} · {active.minute??'?'}:{String(active.second??0).padStart(2,'0')} · {active.outcome||'Sonuç belirtilmemiş'}<small>Şut türü: {active.shot_type||'Bilinmiyor'} · Kaynak xG: {fmt(active.statsbomb_xg)} · Varsayımsal sağ kale uzaklığı: {geometry(active)?geometry(active)!.distance.toFixed(1)+' m':'—'} · Varsayımsal şut açısı: {geometry(active)?geometry(active)!.angle.toFixed(1)+'°':'—'} · Olay ID: {active.event_id||'—'} · Konum: {active.location?.join(', ')||'Yok'}</small></div>}
 <details><summary>Oyuncu bazında şut kalitesi ({playerStats.length})</summary><div className="tq-shot-table-wrap"><table className="tq-shot-table"><thead><tr><th>Oyuncu</th><th>Takım</th><th>Şut</th><th>Gol etiketi</th><th>Kaynak xG</th><th>xG / şut</th><th>xG kapsamı</th></tr></thead><tbody>{playerStats.map(p=><tr key={p.name+'-'+p.team}><td>{p.name}</td><td>{p.team}</td><td>{p.count}</td><td>{p.goals}</td><td>{p.covered===p.count?p.xg.toFixed(2):'Eksik'}</td><td>{p.covered===p.count?(p.xg/p.count).toFixed(3):'—'}</td><td>{p.covered}/{p.count}</td></tr>)}</tbody></table></div><p>Oyuncu tablosu seçili takım ve şut sonucu filtrelerini takip eder.</p></details>
 <details><summary>Şut olayları ({shots.length})</summary><div className="tq-shot-list">{shots.map(s=><button key={s.index} type="button" aria-pressed={String(s.index)===selected} onClick={()=>selectShot(s)}>{s.minute??'?'}' · {s.team||'—'} · {s.player||'—'} · {s.outcome||'—'}{!s.location?' · Konum eksik':''}</button>)}</div></details>
 <p>Mesafe ve açı, standart 105 × 68 m saha ve sağdaki kale merkezi varsayımıyla yaklaşık hesaplanır; doğrulanmış hücum yönü değildir. Kaynak xG değerleri yeniden hesaplanmaz.</p>
 <p>{report.notes} Veriler yalnızca yerel tarihsel pilot dosyasından gelir; ticari kullanım izni doğrulanmadı.</p>
 </>}
 </section>;
}
