import React, {useEffect,useState} from 'react';
type MapData={status:string;reason?:string;grid?:number[][];columns?:number;rows?:number;plotted_events?:number;missing_location_events?:number;warning?:string};
type CompareData={status:string;delta_total?:number;team_a?:MapData;team_b?:MapData;delta_grid?:number[][];warning?:string};
type DirectionStatus={available:boolean;reason?:string;verification_status?:string;evidence_note?:string};
type Catalog={status:string;teams:{id:number;name:string;players:{id:number;name:string}[]}[];event_types:string[]};
export default function HistoricalHeatmap(){
 const [catalog,setCatalog]=useState<Catalog|null>(null);
 useEffect(()=>{const controller=new AbortController();fetch('/api/v1/heatmap/catalog',{signal:controller.signal}).then(r=>{if(!r.ok)throw new Error('Catalog unavailable');return r.json()}).then(setCatalog).catch(()=>{});return()=>controller.abort()},[]);
 const [compareTeam,setCompareTeam]=useState('');const [comparison,setComparison]=useState<CompareData|null>(null);
 const [team,setTeam]=useState('');const [player,setPlayer]=useState('');const [period,setPeriod]=useState('');const [kind,setKind]=useState('');const [data,setData]=useState<MapData|null>(null);
 const selectedTeam=catalog?.teams.find(t=>String(t.id)===team);
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
 const [selectedZone,setSelectedZone]=useState<{row:number;col:number}|null>(null);
 useEffect(()=>setSelectedZone(null),[team,compareTeam,player,period,kind,normalize]);
 return <><style>{tqStyles}</style><section className="heatmap-panel"><h3>Historical Event Heatmap</h3>
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
  {comparison&&<section className="tq-comparison" aria-label="Takım yoğunluk karşılaştırması"><div className="tq-subhead"><h4>Takım karşılaştırması</h4><span>Kaynak olay yoğunluğu · Taktik üstünlük değildir</span></div>{comparison.status==='insufficient_data'?<p role="status">Karşılaştırma için iki takımda da konumlu olay bulunmalı.</p>:<><div className="tq-metrics"><div><small>{selectedTeam?.name||'Takım A'}</small><strong>{comparison.team_a?.plotted_events??'—'}</strong><span>Konumlu olay</span></div><div><small>{catalog?.teams.find(t=>String(t.id)===compareTeam)?.name||'Takım B'}</small><strong>{comparison.team_b?.plotted_events??'—'}</strong><span>Konumlu olay</span></div><div><small>Fark (A − B)</small><strong>{comparison.delta_total??'—'}</strong><span>Ham olay sayısı</span></div></div><div className="tq-side-by-side"><div><h5>{selectedTeam?.name||'Takım A'}</h5><PitchHeatmap grid={comparison.team_a?.grid||[]} mode="single" selectedZone={selectedZone} onSelectZone={setSelectedZone}/></div><div><h5>{catalog?.teams.find(t=>String(t.id)===compareTeam)?.name||'Takım B'}</h5><PitchHeatmap grid={comparison.team_b?.grid||[]} mode="single" selectedZone={selectedZone} onSelectZone={setSelectedZone}/></div></div><ZoneReadout zone={selectedZone} comparison={comparison}/><details className="tq-details"><summary>Fark haritasını göster (A − B)</summary><ComparisonPitch comparison={comparison} normalized={normalize} teamA={selectedTeam?.name||'Takım A'} teamB={catalog?.teams.find(t=>String(t.id)===compareTeam)?.name||'Takım B'}/></details><details className="tq-details"><summary>Bölge bazında sayısal fark (A − B)</summary><pre className="heatmap-grid-text">{comparison.delta_grid?.map(row=>row.join('  ')).join('\n')}</pre></details></>}{comparison.warning&&<p className="heatmap-note">{comparison.warning}</p>}</section>}
  {data?.status==='insufficient_data'&&<p role="status">Konum verisi bulunamadı. {data.reason||''}</p>}
  {data?.grid&&data.status==='event_density'&&<section className="tq-visual"><div className="tq-subhead"><h4>{selectedTeam?.name||'Takım'} · Olay yoğunluğu</h4><span>{kind||'Tüm olaylar'} · {period?'Devre '+period:'Tüm maç'}</span></div>{!comparison&&<PitchHeatmap grid={data.grid} mode="single" selectedZone={selectedZone} onSelectZone={setSelectedZone}/>} {!comparison&&<ZoneReadout zone={selectedZone} data={data}/>} <p className="tq-legend">Düşük yoğunluk <span className="tq-scale"/> Yüksek yoğunluk</p><p className="heatmap-note">{data.plotted_events} konumlu olay · {data.missing_location_events} eksik konum · {normalize?'Doğrulanmış yön bilgisiyle normalize edildi.':'Hücum yönü normalize edilmedi.'}</p><details className="tq-details"><summary>Sayısal yoğunluk tablosu</summary><pre className="heatmap-grid-text">{data.grid.map(row=>row.join('  ')).join('\n')}</pre></details></section>}
 </section></>
}

type Zone={row:number;col:number};
function ZoneReadout({zone,data,comparison}:{zone:Zone|null;data?:MapData;comparison?:CompareData}){
 if(!zone)return <p className="tq-zone-help">Sahadaki bir bölgeyi seçerek kaynak olay sayılarını inceleyin.</p>;
 const count=(g?:number[][])=>g?.[zone.row]?.[zone.col]??0;
 return <div className="tq-zone-readout" role="status"><strong>Bölge {zone.row+1} · {zone.col+1}</strong>{comparison?<span>Takım A: {count(comparison.team_a?.grid)} · Takım B: {count(comparison.team_b?.grid)} · Fark: {count(comparison.delta_grid)}</span>:<span>Olay sayısı: {count(data?.grid)}</span>}<small>Bu değerler seçili grid hücresindeki ham olay sayılarıdır; oyuncu tracking verisi değildir.</small></div>;
}
function PitchHeatmap({grid,mode,selectedZone,onSelectZone}:{grid:number[][];mode:'single'|'difference';selectedZone?:Zone|null;onSelectZone?:(zone:Zone)=>void}){
 const rows=grid.length,cols=grid[0]?.length||0;
 if(!rows||!cols)return <p>Harita verisi yok.</p>;
 const peak=Math.max(1,...grid.flat().map(Math.abs));
 const cellW=600/cols,cellH=390/rows;
 const values=grid.flat().filter(n=>n>0).sort((a,b)=>a-b);
 const reference=Math.max(1,values[Math.floor(values.length*.85)]||peak);
 return <svg className="tq-pitch" viewBox="0 0 640 430" role="img" aria-label={mode==='single'?'Gerçek olay sayılarından hesaplanan saha yoğunluk haritası':'İki takımın ham koordinatlarda olay yoğunluğu farkı'}>
 <defs><radialGradient id="tqWarmV3"><stop offset="0%" stopColor="#FFD16E" stopOpacity=".9"/><stop offset="35%" stopColor="#F18448" stopOpacity=".52"/><stop offset="100%" stopColor="#F18448" stopOpacity="0"/></radialGradient><radialGradient id="tqCoolV3"><stop offset="0%" stopColor="#62D8D0" stopOpacity=".85"/><stop offset="100%" stopColor="#62D8D0" stopOpacity="0"/></radialGradient></defs>
 <rect width="640" height="430" rx="14" fill="#133B36"/>
 {Array.from({length:10},(_,i)=><rect key={i} x={20+i*60} y="20" width="60" height="390" fill={i%2?'#FFFFFF':'#000000'} opacity=".035"/>)}
 <g>{grid.flatMap((row,r)=>row.map((n,c)=>{if(!n)return null;const intensity=Math.min(1,Math.abs(n)/(mode==='single'?reference:peak));return <ellipse key={r+'-'+c} cx={20+(c+.5)*cellW} cy={20+(r+.5)*cellH} rx={cellW*1.15} ry={cellH*1.2} fill={mode==='difference'&&n<0?'url(#tqCoolV3)':'url(#tqWarmV3)'} opacity={Math.min(.88,.08+Math.pow(intensity,1.4)*.78)}><title>{'Bölge '+(r+1)+','+(c+1)+': '+n+' olay'}</title></ellipse>}))}</g>
 <g stroke="#D4F1E9" strokeWidth="1.6" fill="none" opacity=".9" pointerEvents="none"><rect x="20" y="20" width="600" height="390"/><path d="M320 20V410"/><circle cx="320" cy="215" r="64"/><circle cx="320" cy="215" r="2" fill="#D4F1E9"/><rect x="20" y="115" width="102" height="200"/><rect x="20" y="161" width="38" height="108"/><rect x="518" y="115" width="102" height="200"/><rect x="582" y="161" width="38" height="108"/><path d="M122 174 A58 58 0 0 1 122 256 M518 174 A58 58 0 0 0 518 256"/></g>
 {onSelectZone&&grid.flatMap((row,r)=>row.map((n,c)=><rect key={'hit-'+r+'-'+c} x={20+c*cellW} y={20+r*cellH} width={cellW} height={cellH} fill={selectedZone?.row===r&&selectedZone.col===c?'#FFFFFF':'transparent'} fillOpacity={selectedZone?.row===r&&selectedZone.col===c?.13:0} stroke={selectedZone?.row===r&&selectedZone.col===c?'#F8E7B7':'none'} strokeWidth="2" role="button" tabIndex={0} aria-label={'Bölge '+(r+1)+','+(c+1)+': '+n+' olay'} onClick={()=>onSelectZone({row:r,col:c})} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelectZone({row:r,col:c})}}} style={{cursor:'pointer'}}><title>{n} olay · Bölge {r+1},{c+1}</title></rect>))}
 </svg>;
}
function ComparisonPitch({comparison,normalized,teamA,teamB}:{comparison:CompareData;normalized:boolean;teamA:string;teamB:string}){
 const grid=comparison.delta_grid;
 if(!grid?.length||!grid[0]?.length)return <p role="status">Karşılaştırılacak bölge yok.</p>;
 const rows=grid.length,cols=grid[0].length,cw=600/cols,ch=390/rows;
 const [zone,setZone]=React.useState<Zone|null>(null);
 const [displayMode,setDisplayMode]=React.useState<'percent'|'raw'>('percent');
 const totalA=comparison.team_a?.grid?.flat().reduce((sum,n)=>sum+n,0)||0;
 const totalB=comparison.team_b?.grid?.flat().reduce((sum,n)=>sum+n,0)||0;
 const shownGrid=grid.map((row,ri)=>row.map((raw,ci)=>displayMode==='raw'?raw:(totalA&&totalB?100*((comparison.team_a?.grid?.[ri]?.[ci]||0)/totalA-(comparison.team_b?.grid?.[ri]?.[ci]||0)/totalB):0)));
 const maxShown=Math.max(1e-9,...shownGrid.flat().map(Math.abs));
 const count=(g?:number[][])=>zone?g?.[zone.row]?.[zone.col]??0:0;
 return <div className="tq-compare-pitch">
 <div className="tq-mode-switch" role="group" aria-label="Fark haritası karşılaştırma yöntemi"><button type="button" aria-pressed={displayMode==='percent'} onClick={()=>{setDisplayMode('percent');setZone(null)}}>Yüzdesel dağılım</button><button type="button" aria-pressed={displayMode==='raw'} onClick={()=>{setDisplayMode('raw');setZone(null)}}>Ham sayı</button></div><p className="tq-zone-help">{displayMode==='percent'?'Her bölgenin takımın toplam konumlu olayları içindeki payı karşılaştırılır (yüzde puan farkı). Toplam olay sayısı eşitlenmez; dağılım karşılaştırılır.':'Her bölgedeki ham olay sayılarının farkı gösterilir.'}</p>
 <div className="tq-diff-key"><span><i className="tq-key-color tq-key-a"/>{teamA} daha fazla</span><span><i className="tq-key-color tq-key-b"/>{teamB} daha fazla</span><span><i className="tq-key-color tq-key-equal"/>Eşit</span></div>
 <svg className="tq-pitch" viewBox="0 0 640 430" role="img" aria-label={teamA+' ve '+teamB+' arasındaki ham olay farkı, bölge bazında'}>
 <rect width="640" height="430" rx="14" fill="#123B36"/>
 {shownGrid.flatMap((row,ri)=>row.map((n,ci)=>{const strength=Math.abs(n)/maxShown;const fill=n>0?'#EF8748':n<0?'#32C6C3':'#526A69';const selected=zone?.row===ri&&zone.col===ci;return <rect key={ri+'-'+ci} x={20+ci*cw} y={20+ri*ch} width={cw} height={ch} fill={fill} fillOpacity={n===0?.35:.28+.62*Math.sqrt(strength)} stroke={selected?'#FFFFFF':'#FFFFFF'} strokeOpacity={selected?1:.14} strokeWidth={selected?2:.5} role="button" tabIndex={0} aria-label={'Bölge '+(ri+1)+','+(ci+1)+': '+(n>0?teamA+' '+n:n<0?teamB+' '+Math.abs(n):'eşit')+(displayMode==='percent'?' yüzde puan farkı':' olay farkı')} onClick={()=>setZone({row:ri,col:ci})} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setZone({row:ri,col:ci})}}} style={{cursor:'pointer'}}><title>{'Bölge '+(ri+1)+','+(ci+1)+' · '+teamA+': '+(comparison.team_a?.grid?.[ri]?.[ci]??0)+' · '+teamB+': '+(comparison.team_b?.grid?.[ri]?.[ci]??0)}</title></rect>}))}
 <g stroke="#E1F3EC" strokeWidth="1.7" fill="none" opacity=".9" pointerEvents="none"><rect x="20" y="20" width="600" height="390"/><path d="M320 20V410"/><circle cx="320" cy="215" r="64"/><circle cx="320" cy="215" r="2" fill="#E1F3EC"/><rect x="20" y="115" width="102" height="200"/><rect x="20" y="161" width="38" height="108"/><rect x="518" y="115" width="102" height="200"/><rect x="582" y="161" width="38" height="108"/><path d="M122 174 A58 58 0 0 1 122 256 M518 174 A58 58 0 0 0 518 256"/></g>
 </svg>
 {zone?<div className="tq-zone-readout" role="status"><strong>Bölge {zone.row+1} · {zone.col+1}</strong><span>{teamA}: {count(comparison.team_a?.grid)} ({totalA?(100*count(comparison.team_a?.grid)/totalA).toFixed(2):'—'}%) · {teamB}: {count(comparison.team_b?.grid)} ({totalB?(100*count(comparison.team_b?.grid)/totalB).toFixed(2):'—'}%) · {displayMode==='percent'?'Pay farkı: '+shownGrid[zone.row][zone.col].toFixed(2)+' yüzde puan':'Ham fark: '+count(grid)}</span></div>:<p className="tq-zone-help">Bölgeye tıklayarak iki takımın gerçek olay sayılarını karşılaştırın.</p>}
 <p className="heatmap-note">Renkler seçilen yönteme göre aynı koordinat bölgesindeki olay sayısı veya olay payı farkını gösterir; taktik üstünlük veya tracking değildir. {normalized?'Hücum yönleri doğrulandı.':'Hücum yönleri normalize edilmedi.'}</p>
 </div>;
}
const tqStyles=`
.heatmap-panel{background:#101e30;border:1px solid #294158;border-radius:18px;padding:24px;color:#e8f1fa}
.heatmap-panel h3{font-size:22px;letter-spacing:-.4px;margin:0 0 8px}
.heatmap-panel .heatmap-controls{display:flex;flex-wrap:wrap;gap:14px;align-items:end;margin:22px 0}
.heatmap-panel .heatmap-controls label{display:flex;flex-direction:column;gap:8px;color:#b6c9d9;font-size:12px}
.heatmap-panel select,.heatmap-panel input:not([type=checkbox]){background:#182b41;border:1px solid #39536b;color:#f3f8fd;border-radius:9px;padding:11px;min-height:42px}
.heatmap-panel button{background:#367ef2;border:0;border-radius:9px;color:white;padding:12px 18px;font-weight:650;cursor:pointer}
.heatmap-panel button:disabled{opacity:.5;cursor:not-allowed}
.tq-comparison,.tq-visual{background:#142438;border:1px solid #2a4157;border-radius:15px;padding:18px;margin:20px 0}
.tq-subhead{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px;margin-bottom:15px}
.tq-subhead h4{font-size:17px;margin:0}.tq-subhead span{font-size:12px;color:#9eb3c7}
.tq-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-bottom:16px}
.tq-metrics>div{display:flex;flex-direction:column;gap:5px;background:#1b3046;border:1px solid #304a61;border-radius:11px;padding:14px}
.tq-metrics small,.tq-metrics span{color:#aabfd0;font-size:12px}.tq-metrics strong{font-size:25px;letter-spacing:-.5px}
.tq-pitch{display:block;width:100%;max-width:820px;margin:0 auto;border-radius:13px;overflow:hidden}
.tq-legend{display:flex;gap:9px;align-items:center;justify-content:center;color:#aebfce;font-size:12px;margin:12px 0}
.tq-scale{width:115px;height:9px;border-radius:10px;background:linear-gradient(90deg,#16443f,#ec7046,#ffd174)}
.tq-dot{width:10px;height:10px;border-radius:50%;display:inline-block}.tq-orange{background:#f89b55}.tq-teal{background:#61d4d0}
 .tq-side-by-side{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.tq-side-by-side>div{background:#102b35;border:1px solid #2b4c55;border-radius:12px;padding:12px;min-width:0}.tq-side-by-side h5{font-size:14px;margin:0 0 10px;color:#e4f0f6}.tq-zone-readout{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-top:14px;padding:12px;background:#1c3345;border-radius:10px}.tq-zone-readout small{width:100%;color:#a7bdca}.tq-zone-help{font-size:12px;color:#a7bdca;margin:12px 0}.tq-mode-switch{display:flex;justify-content:center;gap:8px;margin:12px 0}.tq-mode-switch button{background:#1a3446;border:1px solid #3c6274;color:#d6e8ef;border-radius:8px;padding:9px 14px}.tq-mode-switch button[aria-pressed=true]{background:#235a72;border-color:#69c8e0;color:#fff}.tq-diff-key{display:flex;flex-wrap:wrap;justify-content:center;gap:16px;margin:10px 0 16px;font-size:13px;color:#d8e6ef}.tq-diff-key span{display:flex;align-items:center;gap:7px}.tq-key-color{width:14px;height:14px;border-radius:3px;display:inline-block}.tq-key-a{background:#EF8748}.tq-key-b{background:#32C6C3}.tq-key-equal{background:#526A69}.tq-details{margin-top:14px;color:#b9c9d9}.tq-details summary{cursor:pointer;padding:8px}.tq-details pre{overflow:auto}
@media(max-width:760px){.tq-side-by-side{grid-template-columns:1fr}}@media(max-width:600px){.heatmap-panel{padding:14px}.tq-metrics{grid-template-columns:1fr}.tq-comparison,.tq-visual{padding:12px}}
`;
