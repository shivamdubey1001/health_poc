import { useEffect,useState } from 'react'
import { useNavigate,useParams } from 'react-router-dom'
import { MapPin, ShieldAlert } from 'lucide-react'
import { api } from '../services/api'
import type { Member,Readiness } from '../types/api'
import { PageHeader } from '../components/PageHeader'
import { MemberHeader } from '../components/MemberHeader'
import { LoadingState } from '../components/LoadingState'
import { ErrorState } from '../components/ErrorState'
import { ReadinessGauge } from '../components/ReadinessGauge'
import { StatusBadge } from '../components/StatusBadge'

export default function ReadinessPage(){
  const {memberId=''}=useParams();const [member,setMember]=useState<Member>();const [r,setR]=useState<Readiness>();const [err,setErr]=useState('');const nav=useNavigate()
  useEffect(()=>{Promise.all([api.member(memberId),api.latestReadiness(memberId)]).then(([m,rr])=>{setMember(m);setR(rr)}).catch(e=>setErr(e.message))},[memberId])
  if(err)return <><PageHeader title="Readiness" subtitle="This page only displays a readiness assessment that was explicitly run."/><ErrorState message={err}/><button className="btn-secondary mt-4" onClick={()=>nav('/assessment-results')}>Back to Scan Results</button></>
  if(!member||!r)return <LoadingState label="Loading completed readiness assessment…"/>
  return <><PageHeader title="Administrative Readiness" subtitle="Deterministic plan and network facts are separated from OpenAI prioritization. Opening this page creates no new model call."/><MemberHeader member={member}/><div className="grid gap-5 xl:grid-cols-3"><section className="card xl:col-span-1"><ReadinessGauge score={r.readiness_score} label={r.readiness_label}/>{r.score_explanation.length>0&&<div className="mt-5 border-t border-line pt-4"><p className="text-sm font-semibold">Why the score changed</p><ul className="mt-2 space-y-1 text-sm text-muted">{r.score_explanation.map(x=><li key={x}>{x}</li>)}</ul></div>}</section><section className="card xl:col-span-2"><p className="eyebrow">Readiness checklist</p><div className="mt-4 grid gap-3 sm:grid-cols-2">{r.checklist.map(i=><div key={i.key} className="rounded-xl border border-line p-4"><div className="flex items-start justify-between gap-3"><p className="font-semibold">{i.label}</p><StatusBadge status={i.status}/></div><p className="mt-2 text-sm leading-5 text-muted">{i.detail}</p></div>)}</div></section></div><section className="card mt-5"><div className="flex items-start gap-3"><ShieldAlert className="mt-0.5 text-brand" size={20}/><div><p className="eyebrow">Recommended next action</p><h2 className="section-title mt-1">{r.recommended_next_action}</h2>{r.top_issue&&<p className="mt-1 text-sm text-muted">Top issue: {r.top_issue}</p>}<p className="mt-2 text-xs text-muted">{r.generated_by}</p></div></div>{r.alternatives.length>0&&<div className="mt-5 border-t border-line pt-5"><p className="section-title">In-network alternatives</p><p className="mt-1 text-sm text-muted">Retrieved only from the synthetic provider directory and plan network table.</p><div className="mt-4 grid gap-3 md:grid-cols-3">{r.alternatives.map(a=><div key={a.provider_id} className="rounded-xl border border-line p-4"><p className="font-semibold">{a.provider_name}</p><p className="mt-1 text-sm text-muted">{a.organization_name}</p><div className="mt-3 flex items-center gap-2 text-xs text-muted"><MapPin size={14}/>{a.city}, {a.state} · ZIP3 {a.zip3}</div><div className="mt-3"><StatusBadge status="READY"/></div></div>)}</div></div>}</section><div className="mt-5 flex justify-end"><button className="btn-primary" onClick={()=>nav(`/members/${memberId}/outreach`)}>Review proactive outreach</button></div></>
}
