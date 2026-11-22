import React, {useState} from 'react';

// Source: StatsBomb Open Data, events/3773386.json, indices 5, 7, 10, 13.
// These are sourced observations, NOT a complete-match calculation.
const passes = [
 {id:'208f072d-cffa-4575-bd73-e9e9384c8fe1',time:'00:00.689',player:'Antoine Griezmann',to:'Sergio Busquets',from:[61,40.1],end:[50,45.4],length:12.210241},
 {id:'e1f11e14-fb24-4c82-868f-507385122b9c',time:'00:01.653',player:'Sergio Busquets',to:'Frenkie de Jong',from:[49.4,44.9],end:[47.1,29.6],length:15.47191},
 {id:'4d801bc4-907a-4474-9620-7c6ca2610ea7',time:'00:05.344',player:'Frenkie de Jong',to:'Gerard Piqué',from:[48.1,29.6],end:[35.5,50.6],length:24.489998},
 {id:'72a0c004-6d76-4ea8-b892-0f7881be9320',time:'00:10.283',player:'Gerard Piqué',to:'Clément Lenglet',from:[44.3,50.2],end:[41,29.7],length:20.76391},
] as const;
const x=(n:number)=>12+n*3;
const y=(n:number)=>12+n*2.25;
export default function VerifiedKickoff(){
 const [selected,setSelected]=useState(0);
 return <section className="verified-kickoff" aria-label="Barcelona Alavés historical verified event sample">
  <div className="kickoff-head"><div><div className="eyebrow">SOURCE-BACKED EVENT EXPLORER</div><h3>Barcelona → Alavés · 31.10.2020</h3></div><span className="pill">4 source events</span></div>
  <p>StatsBomb maç #3773386 · Başlangıçtaki dört pas. Bu bir <strong>kısmi kanıt örneği</strong>; tam maç verisi veya canlı API sonucu değildir.</p>
  <svg viewBox="0 0 384 204" role="img" aria-label="Four sourced Barcelona passes plotted on a StatsBomb 120 by 80 coordinate pitch" style={{width:'100%',maxWidth:760,background:'#123b31',borderRadius:10}}>
   <rect x="12" y="12" width="360" height="180" fill="none" stroke="#9dbeb4" strokeWidth="1.4"/><path d="M192 12V192" stroke="#9dbeb4" fill="none"/><circle cx="192" cy="102" r="30" stroke="#9dbeb4" fill="none"/><rect x="12" y="60" width="48" height="84" fill="none" stroke="#9dbeb4"/><rect x="324" y="60" width="48" height="84" fill="none" stroke="#9dbeb4"/>
   {passes.map((p,i)=><g key={p.id} opacity={i===selected?1:0.36}><line x1={x(p.from[0])} y1={y(p.from[1])} x2={x(p.end[0])} y2={y(p.end[1])} stroke={i===selected?'#c6fa65':'#f4f9e9'} strokeWidth={i===selected?3:1.5}/><circle cx={x(p.from[0])} cy={y(p.from[1])} r={i===selected?5:3} fill="#c6fa65"/><circle cx={x(p.end[0])} cy={y(p.end[1])} r="3" fill="#f4f9e9"/></g>)}
  </svg>
  <div className="kickoff-controls" aria-label="Select a sourced pass">{passes.map((p,i)=><button type="button" key={p.id} aria-pressed={selected===i} onClick={()=>setSelected(i)}>{i+1}. {p.player}</button>)}</div>
  <div className="kickoff-detail"><strong>{passes[selected].player} → {passes[selected].to}</strong><p>Olay zamanı: {passes[selected].time} · Pas uzunluğu: {passes[selected].length.toFixed(2)} m · Başlangıç: [{passes[selected].from.join(', ')}] · Bitiş: [{passes[selected].end.join(', ')}]</p><small>Event ID: <code>{passes[selected].id}</code></small></div>
  <p className="kickoff-source">Kaynak: <a href="https://raw.githubusercontent.com/statsbomb/open-data/master/data/events/3773386.json" target="_blank" rel="noreferrer">StatsBomb Open Data / events/3773386.json</a>. Sahadaki çizgiler olay koordinatlarını gösterir; oyuncuların topsuz hareketi değildir.</p>
 </section>;
}
