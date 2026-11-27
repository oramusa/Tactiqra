import {validateCoachPlan} from './coachValidation.ts';
const scenarioNames=['Hücum','Savunma','Geçiş','Korner','Serbest vuruş'] as const;
const phaseNames=['In Possession','Out of Possession','Transition'] as const;
export function approveBriefing<T extends {scenario:string;opponent:string;phases:Record<typeof phaseNames[number],{board:{task:string}[]}>}>(plans:T[],confirmed:boolean,approvedAt:string):{version:1;approvedAt:string;scenarios:T[]} {
  if(!confirmed||plans.length!==scenarioNames.length)throw Error('Tüm senaryoları inceleyin.');
  if(new Set(plans.map(p=>p.scenario)).size!==scenarioNames.length||!scenarioNames.every(n=>plans.some(p=>p.scenario===n)))throw Error('Eksik veya tekrarlanan senaryo.');
  plans.forEach(p=>validateCoachPlan(p,p.scenario));
  if(new Set(plans.map(p=>p.opponent.trim().toLowerCase()).filter(Boolean)).size!==1||plans.some(p=>!p.opponent.trim()))throw Error('Tüm senaryolarda aynı rakip belirtilmeli.');
  if(!plans.some(p=>phaseNames.some(n=>p.phases[n].board.some(x=>x.task.trim()))))throw Error('En az bir oyuncu talimatı gerekli.');
  return {version:1,approvedAt,scenarios:JSON.parse(JSON.stringify(plans))};
}
export function isBriefingStale<T>(approved:{scenarios:T[]}|null,plans:T[]):boolean {
 return approved!==null&&JSON.stringify(approved.scenarios)!==JSON.stringify(plans);
}
