import React,{useState} from 'react';
type Side={shots:number;goals_from_shots:number;xg_sum:number|null;xg_count:number;box_shots:number;located_shots:number;goal_event_ids:string[]};
type Match={match_id:number;date:string;home:string;away:string;source:string;status:string;own?:Side;opponent?:Side};
type Result={status:string;requested_matches:number;analyzed_matches:number;matches:Match[];limitations?:string[]};
export default function HistoricalMultiMatch(){
 const [limit,setLimit]=useState(3),[data,setData]=useState<Result|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState('');
 async function run(){setLoading(true);setError('');setData(null);try{const r=await fetch('/api/v1/opponentiq/historical-multi-match?limit='+limit);if(!r.ok)throw new Error('API '+r.status);const d=await r.json();if(!Array.isArray(d.matches))throw new Error('Geçersiz API yanıtı');setData(d)}catch(e){setError(e instanceof Error?e.message:'Veri alınamadı')}finally{setLoading(false)}}
 const valid=(data?.matches||[]).filter(m=>m.status==='provisional'&&m.own&&m.opponent);
 const n=valid.length;
 const sum=(side:'own'|'opponent',key:'shots'|'goals_from_shots'|'box_shots'|'located_shots'|'xg_count')=>valid.reduce((a,m)=>a+m[side]![key],0);
 const complete=(s:'own'|'opponent')=>n>0&&valid.every(m=>m[s]!.xg_count===m[s]!.shots&&m[s]!.xg_sum!==null);
 const xg=(s:'own'|'opponent')=>valid.reduce((a,m)=>a+(m[s]!.xg_sum??0),0);
 const comparable=valid.filter(m=>m.own!.xg_sum!==null&&m.opponent!.xg_sum!==null&&m.own!.xg_count===m.own!.shots&&m.opponent!.xg_count===m.opponent!.shots);
 const bothComplete=complete('own')&&complete('opponent');
 const scored=sum('own','goals_from_shots'), conceded=sum('opponent','goals_from_shots');
 const ownShots=sum('own','shots'), oppShots=sum('opponent','shots');
 const signed=(v:number)=>(v>0?'+':'')+v.toFixed(2);
 const chartMax=Math.max(1,...comparable.flatMap(m=>[m.own!.xg_sum!,m.opponent!.xg_sum!]));
 const ownBelow=comparable.filter(m=>m.own!.goals_from_shots<m.own!.xg_sum!).length;
 const oppAbove=comparable.filter(m=>m.opponent!.goals_from_shots>m.opponent!.xg_sum!).length;
 const ahead=comparable.filter(m=>m.own!.xg_sum!>m.opponent!.xg_sum!).length;
 return <section className="panel" style={{marginTop:20}}><h2>Historical Multi-Match Intelligence</h2><p>Barcelona · LaLiga 2020/21 · StatsBomb Open Data. Güncel takım seçimine bağlı değildir.</p><div className="filters"><label>Maç sayısı <input type="number" min={1} max={5} value={limit} disabled={loading} onChange={e=>setLimit(Math.max(1,Math.min(5,Math.trunc(Number(e.target.value))||1)))}/></label><button disabled={loading} onClick={run}>{loading?'Analiz ediliyor…':'Maçları analiz et'}</button></div>{error&&<p role="alert">{error}</p>}{data&&<><p role="status">Kapsam: {n}/{data.requested_matches??limit} · {data.status}</p>{n>0&&<><div className="metrics">{[['Şutlar',sum('own','shots')+' / '+sum('opponent','shots')],['Şut golleri',sum('own','goals_from_shots')+' / '+sum('opponent','goals_from_shots')],['xG / xGA', (complete('own')?xg('own').toFixed(2):'—')+' / '+(complete('opponent')?xg('opponent').toFixed(2):'—')],['Ceza sahası şutları',sum('own','box_shots')+' / '+sum('own','located_shots')]].map(([label,value])=><div className="metric" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div><div className="metrics">{[
 ['Maç başı xG',complete('own')?(xg('own')/n).toFixed(2):'—'],
 ['Maç başı xGA',complete('opponent')?(xg('opponent')/n).toFixed(2):'—'],
 ['Şut başı xG',complete('own')&&ownShots?(xg('own')/ownShots).toFixed(3):'—'],
 ['Rakip şut başı xG',complete('opponent')&&oppShots?(xg('opponent')/oppShots).toFixed(3):'—'],
 ['Gol − xG',complete('own')?signed(scored-xg('own')):'—'],
 ['Yenilen gol − xGA',complete('opponent')?signed(conceded-xg('opponent')):'—']
 ].map(([label,value])=><div className="metric" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>
 <h3>Maç bazında xG karşılaştırması</h3>
 {comparable.map(m=>{const a=m.own!.xg_sum!,b=m.opponent!.xg_sum!,max=chartMax;return <div key={m.match_id} style={{marginBottom:14}}><strong>{m.date} · {m.home} – {m.away}</strong>{[['Barcelona',a,'#60a5fa'],['Rakip',b,'#f59e0b']].map(([label,value,color])=><div key={String(label)} style={{display:'flex',alignItems:'center',gap:10,marginTop:5}}><span style={{width:85}}>{label}</span><div style={{flex:1,background:'rgba(128,128,128,.15)',height:10,borderRadius:5}}><div style={{width:(Number(value)/max*100)+'%',background:String(color),height:10,borderRadius:5}}/></div><span>{Number(value).toFixed(2)}</span></div>)}</div>})}
 <p className="data-note">Tüm maçlar aynı xG ölçeğinde gösterilir. xG kapsamı eksik maçlar grafiğe alınmaz.</p>
 <h3>Tekrarlanan gözlemler</h3>
 {comparable.length>0&&<div className="metrics">{[
 ['Rakipten yüksek xG',ahead],
 ['xG altında gol üretimi',ownBelow],
 ['xGA üzerinde gol yeme',oppAbove]
 ].map(([label,count])=><div className="metric" key={label}><span>{label}</span><strong>{count}/{comparable.length}</strong><small>Tam xG kapsamlı maçlar</small></div>)}</div>}
 <p className="data-note">Frekanslar betimseldir; küçük örneklemden kalıcı taktik zayıflık çıkarılmaz.</p>
 {bothComplete&&<p>Analiz edilen {n} maçta şut golleri ile xG farkı {signed(scored-xg('own'))}; rakiplerin şut golleri ile xGA farkı {signed(conceded-xg('opponent'))}. Bu farklar tek başına bitiricilik veya savunma becerisi kanıtı değildir.</p>}<p>{comparable.length? 'Barcelona '+ahead+'/'+comparable.length+' tam xG kapsamlı maçta rakibinden daha yüksek xG üretti.':'Karşılaştırılabilir xG verisi yok.'} Bu gözlem taktik neden veya güncel form kanıtı değildir.</p></>}<div style={{overflowX:'auto'}}><table style={{width:'100%',textAlign:'left'}}><thead><tr><th>Tarih / maç</th><th>Şut</th><th>Şut golleri</th><th>xG / xGA</th><th>Kaynak</th></tr></thead><tbody>{data.matches.map(m=><tr key={m.match_id}><td>{m.date} · {m.home} – {m.away}</td><td>{m.own&&m.opponent?m.own.shots+' / '+m.opponent.shots:m.status}</td><td>{m.own&&m.opponent?m.own.goals_from_shots+' / '+m.opponent.goals_from_shots:'—'}</td><td>{[m.own,m.opponent].map(s=>s&&s.xg_count===s.shots?s.xg_sum?.toFixed(2)??'—':'—').join(' / ')}</td><td><a href={m.source} target="_blank" rel="noreferrer">StatsBomb {m.match_id}</a>{m.own&&m.opponent&&<details><summary>Gol olay kimlikleri</summary><p>Barcelona: {m.own.goal_event_ids.join(', ')||'Yok'}</p><p>Rakip: {m.opponent.goal_event_ids.join(', ')||'Yok'}</p></details>}</td></tr>)}</tbody></table></div>{data.limitations?.map(l=><p key={l} className="data-note">{l}</p>)}</>}</section>
}
