import React, {useEffect,useState} from 'react';
type MapData={status:string;reason?:string;grid?:number[][];columns?:number;rows?:number;plotted_events?:number;missing_location_events?:number;warning?:string};
type CompareData={status:string;delta_total?:number;team_a?:MapData;team_b?:MapData;delta_grid?:number[][];warning?:string};
type DirectionStatus={available:boolean;reason?:string;verification_status?:string;evidence_note?:string};
type Catalog={status:string;teams:{id:number;name:string;players:{id:number;name:string}[]}[];event_types:string[]};
export default function HistoricalHeatmap(){
 const [catalog,setCatalog]=useState<Catalog|null>(null);
 useEffect(()=>{const controller=new AbortController();fetch('/api/v1/heatmap/catalog',{signal:controller.signal}).then(r=>{if(!r.ok)throw new Error('Catalog unavailable');return r.json()}).then(setCatalog).catch(()=>{});return()=>controller.abort()},[]);
 const selectedTeam=catalog?.teams.find(t=>String(t.id)===team);
 const [compareTeam,setCompareTeam]=useState('');const [comparison,setComparison]=useState<CompareData|null>(null);
 const [team,setTeam]=useState('');const [player,setPlayer]=useState('');const [period,setPeriod]=useState('');const [kind,setKind]=useState('');const [data,setData]=useState<MapData|null>(null);
 const [error,setError]=useState('');const [loading,setLoading]=useState(false);
 const [normalize,setNormalize]=useState(false);const [direction,setDirection]=useState<DirectionStatus|null>(null);const [directionLoading,setDirectionLoading]=useState(false);
 useEffect(()=>{setData(null);setComparison(null);setError('')},[team,compareTeam,player,period,kind,normalize]);
 useEffect(()=>{setDirection(null);setNormalize(false);if(!team)return;const c=new AbortController();setDirectionLoading(true);const q=new URLSearchParams({team_id:team});if(compareTeam&&!player)q.set('opponent_id',compareTeam);fetch('/api/v1/heatmap/direction-status?'+q,{signal:c.signal}).then(async r=>{if(!r.ok)throw new Error('Direction status unavailable');return r.json()}).then(setDirection).catch(e=>{if(e.name!=='AbortError')setDirection({available:false,reason:e.message})}).finally(()=>{if(!c.signal.aborted)setDirectionLoading(false)});return()=>c.abort()},[team,compareTeam,player]);
 const load=async()=>{setLoading(true);setError('');try{
   if(!/^\d+$/.test(team))throw new Error('Geçerli tarihsel StatsBomb takım ID girin');
   if(player && !/^\d+$/.test(player))throw new Error('Oyuncu ID sayısal olmalı');
   const params=new URLSearchParams({team_id:team});if(kind)params.set('event_type',kind);if(player)params.set('player_id',player);if(period)params.set('period',period);if(normalize)params.set('normalize','true');
   const response=await fetch('/api/v1/heatmap/events?'+params.toString());
   if(!response.ok)throw new Error('Heatmap API unavailable');setData(await response.json());
   if(compareTeam && !player){const compareParams=new URLSearchParams({team_a:team,team_b:compareTeam});if(kind)compareParams.set('event_type',kind);if(period)compareParams.set('period',period);if(normalize)compareParams.set('normalize','true');const cr=await fetch('/api/v1/heatmap/compare?'+compareParams.toString());if(!cr.ok)throw new Error('Comparison API unavailable');setComparison(await cr.json())}
  }catch(e){setError(e instanceof Error?e.message:String(e))}finally{setLoading(false)}};
 const max=data?.grid?Math.max(0,...data.grid.flat()):0;
 return <section className="heatmap-panel"><h3>Historical Event Heatmap</h3>
  <p className="heatmap-note">Bağımsız tarihsel pilot. Yukarıda seçilen güncel takımın verisi değildir. Oyuncu tracking haritası değildir.</p>
  <div className="heatmap-controls"><label>StatsBomb takımı{catalog?.teams.length?<select value={team} onChange={e=>{setTeam(e.target.value);setPlayer('')}}><option value="">Takım seç</option>{catalog.teams.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select>:<input inputMode="numeric" value={team} onChange={e=>setTeam(e.target.value)} placeholder="Yerel veri yoksa takım ID"/>}</label>
  <label>Rakip takım (isteğe bağlı)<select value={compareTeam} onChange={e=>setCompareTeam(e.target.value)}><option value="">Karşılaştırma yok</option>{catalog?.teams.filter(t=>String(t.id)!==team).map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
  <label>Oyuncu<select value={player} onChange={e=>setPlayer(e.target.value)}><option value="">Takım geneli</option>{selectedTeam?.players.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
  <label>Devre<select value={period} onChange={e=>setPeriod(e.target.value)}><option value="">Tüm maç</option><option value="1">İlk devre</option><option value="2">İkinci devre</option><option value="3">Uzatma 1</option><option value="4">Uzatma 2</option></select></label>
  <label>Olay türü<select value={kind} onChange={e=>setKind(e.target.value)}><option value="">Tüm olaylar</option>{(catalog?.event_types.length?catalog.event_types:['Pass','Shot','Interception','Ball Recovery']).map(t=><option key={t} value={t}>{t}</option>)}</select></label>
  <label><input type="checkbox" checked={normalize} disabled={!direction?.available||directionLoading} onChange={e=>setNormalize(e.target.checked)}/> Hücum yönünü normalize et</label>
  <button onClick={load} disabled={loading}>{loading?'Yükleniyor…':'Haritayı oluştur'}</button></div>
  {team&&<p className="heatmap-note" role="status">{directionLoading?'Yön kanıtı kontrol ediliyor…':direction?.available?`Yön doğrulandı: ${direction.evidence_note}`:`Normalizasyon kapalı: ${direction?.reason||'Doğrulanmış yön bilgisi yok'}`}</p>}
  {error&&<p role="alert">{error}</p>}
  {compareTeam&&player&&<p role="status">Rakip karşılaştırması yalnızca takım görünümünde yapılır.</p>}
  {comparison&&<section aria-label="Takım yoğunluk karşılaştırması"><h4>Takım karşılaştırması</h4>{comparison.status==='insufficient_data'?<p role="status">Karşılaştırma için iki takımda da konumlu olay bulunmalı.</p>:<><p>Takım A: {comparison.team_a?.plotted_events} olay · Takım B: {comparison.team_b?.plotted_events} olay · Fark: {comparison.delta_total}</p><ComparisonPitch comparison={comparison} normalized={normalize}/><details><summary>Bölge bazında sayısal fark (A − B)</summary><pre className="heatmap-grid-text">{comparison.delta_grid?.map(row=>row.join('  ')).join('\n')}</pre></details></>}<p className="heatmap-note">{comparison.warning}</p></section>}
  {data?.status==='insufficient_data'&&<p role="status">Konum verisi bulunamadı. {data.reason||''}</p>}
  {data?.grid&&data.status==='event_density'&&<><div className="heatmap-pitch" role="img" aria-label={`${data.plotted_events} olay içeren saha yoğunluk haritası; sayısal hücre tablosu aşağıda`}>
    {data.grid.flatMap((row,r)=>row.map((value,c)=><span key={`${r}-${c}`} title={`Bölge ${r+1},${c+1}: ${value} olay`} style={{background:`rgba(239,106,75,${max?0.07+0.86*value/max:0})`}}/>))}
   </div><p>{data.plotted_events} konumlu olay · {data.missing_location_events} eksik konum · {normalize?'Doğrulanmış yön bilgisiyle normalize edildi.':'Hücum yönü normalize edilmedi.'}</p>
   <details><summary>Sayısal yoğunluk tablosu</summary><pre className="heatmap-grid-text">{data.grid.map(row=>row.join('  ')).join('\n')}</pre></details></>}
 </section>
}

function ComparisonPitch({comparison,normalized}:{comparison:CompareData;normalized:boolean}){
 const grid=comparison.delta_grid;
 if(!grid?.length || !grid[0]?.length)return <p role="status">Karşılaştırılacak bölge yok.</p>;
 const max=Math.max(1,...grid.flat().map(Math.abs));
 const positive=grid.flat().filter(n=>n>0).length;
 const negative=grid.flat().filter(n=>n<0).length;
 return <div className="comparison-visual"><div className="comparison-pitch" role="img" aria-label={`Takım A ${positive} bölgede, Takım B ${negative} bölgede daha fazla kayıtlı olaya sahip. Yeşil A, kırmızı B üstünlüğünü gösterir.`} style={{gridTemplateColumns:`repeat(${grid[0].length},minmax(0,1fr))`,gridTemplateRows:`repeat(${grid.length},minmax(0,1fr))`}}>{grid.flatMap((row,r)=>row.map((n,c)=><span key={`${r}-${c}`} title={`Bölge ${r+1}, ${c+1}: ${n>0?'+':''}${n} olay`} style={{background:n>0?`rgba(49,222,119,${0.12+0.83*n/max})`:n<0?`rgba(235,88,105,${0.12+0.83*(-n)/max})`:'rgba(139,155,173,0.16)'}}/>))}</div><p className="heatmap-note">🟩 Takım A daha fazla olay · 🟥 Takım B daha fazla olay · Gri eşit. Bu, üstün oyun veya gerçek oyuncu hareketi ölçümü değildir; {normalized?'hücum yönleri doğrulanmış bilgiyle normalize edildi.':'hücum yönleri normalize edilmedi.'}</p></div>;
}
