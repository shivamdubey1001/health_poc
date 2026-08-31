import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, ChevronDown, ChevronUp, MapPin } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import { ReadinessGauge } from '../components/ReadinessGauge'
import { StatusBadge } from '../components/StatusBadge'
import { useApp } from '../context/AppContext'
import { api } from '../services/api'
import type { ReadinessBatchResult } from '../types/api'

export default function ReadinessResultsPage(){
  const {readinessBatch,setReadinessBatch,selectedMemberIds}=useApp()
  const nav=useNavigate()
  const [open,setOpen]=useState<string|null>(null)
  const [restoring,setRestoring]=useState(false)

  // Results live server-side now, so a page reload can rebuild them rather than
  // showing an empty state. Clinical predictions are deliberately not kept in
  // browser storage on what may be a shared advocate workstation.
  useEffect(()=>{
    if(readinessBatch||!selectedMemberIds.length)return
    let live=true
    setRestoring(true)
    Promise.all(selectedMemberIds.map(async id=>{
      try{
        const [member,care_intent,readiness]=await Promise.all([
          api.member(id),api.latestCareIntent(id),api.latestReadiness(id),
        ])
        return {member,care_intent,readiness}
      }catch{ return null }
    })).then(rows=>{
      if(!live)return
      const found=rows.filter(Boolean) as ReadinessBatchResult['results']
      if(found.length){
        setReadinessBatch({selected_count:selectedMemberIds.length,processed_count:found.length,
          model:'',results:found,skipped:[]})
      }
      setRestoring(false)
    })
    return ()=>{live=false}
  },[readinessBatch,selectedMemberIds,setReadinessBatch])

  if(restoring)return <><PageHeader title="Administrative readiness" subtitle="Reloading saved assessments."/><LoadingState label="Restoring readiness results…"/></>
  if(!readinessBatch)return <><PageHeader title="Readiness Results" subtitle="No Agent 2 assessment has been run yet."/><ErrorState message="Run Agent 1 first, select eligible members on Scan Results, then click Run readiness assessment."/><button className="btn-primary mt-4" onClick={()=>nav('/assessment-results')}>Go to Scan Results</button></>

  const rows=(readinessBatch.results||[]).filter(r=>r&&r.member&&r.readiness)
  const skipped=readinessBatch.skipped||[]
  return <>
    <PageHeader title="Administrative readiness" subtitle={`Agent 2 ran only for the ${rows.length} members you explicitly selected. No readiness work was triggered automatically.`}/>
    <div className="mb-5 rounded-lg border border-brand/20 bg-brand-soft p-4"><p className="eyebrow">Step 3 · Agent 2 results</p><p className="mt-1 text-xl font-semibold">{rows.length} readiness assessment{rows.length===1?'':'s'} completed</p><p className="mt-1 text-sm text-muted">Deterministic plan/network/authorization facts determine the checklist and score. OpenAI prioritizes the unresolved administrative action without changing those facts.</p></div>
    {skipped.length>0&&<div className="mb-5 rounded-lg border border-amber-200 bg-amber-50 p-4">
      <div className="flex items-start gap-3"><AlertTriangle className="mt-0.5 shrink-0 text-amber-700" size={18}/>
        <div><p className="text-sm font-semibold text-amber-900">{skipped.length} member{skipped.length===1?'':'s'} could not be assessed</p>
        <ul className="mt-2 space-y-1 text-sm text-amber-900">{skipped.map(s=><li key={s.member_id}><span className="font-mono">{s.member_id}</span> — {s.reason}</li>)}</ul></div></div></div>}

    {rows.length===0&&<ErrorState message="No readiness assessments completed for the selected members. See the reasons above."/>}

    <div className="space-y-4">{rows.map(({member,care_intent,readiness})=>{const expanded=open===member.member_id;return <article key={member.member_id} className="card p-0 overflow-hidden">
      <div className="grid gap-4 p-5 lg:grid-cols-[1fr_1.1fr_.7fr_1.4fr_auto] lg:items-center">
        <div><p className="font-semibold">{member.name}</p><p className="text-xs text-muted">{member.member_id} · {member.plan_type}</p></div>
        <div><p className="text-xs font-semibold uppercase tracking-wide text-muted">Predicted care</p><p className="mt-1 font-semibold">{readiness.predicted_care_event}</p><p className="text-xs text-muted">Care intent {Math.round(care_intent.care_intent.confidence*100)}%</p></div>
        <div><p className="text-xs font-semibold uppercase tracking-wide text-muted">Readiness</p><p className="mt-1 text-2xl font-bold text-brand-dark">{readiness.readiness_score}%</p><p className="text-xs text-muted">{readiness.readiness_label}</p></div>
        <div><p className="text-xs font-semibold uppercase tracking-wide text-muted">Top issue</p><p className="mt-1 font-semibold">{readiness.top_issue||'No major issue identified'}</p><p className="mt-1 text-xs leading-5 text-muted">{readiness.recommended_next_action}</p></div>
        <div className="flex shrink-0 items-center gap-2 self-start"><button className="btn-primary whitespace-nowrap px-4 py-2 text-sm" onClick={()=>nav(`/members/${member.member_id}/outreach`)}>Review outreach</button>
        <button className="rounded-md p-2 hover:bg-panel" onClick={()=>setOpen(expanded?null:member.member_id)} aria-label="Toggle checklist">{expanded?<ChevronUp size={18}/>:<ChevronDown size={18}/>}</button></div>
      </div>
      {expanded&&<div className="border-t border-line bg-panel/50 p-5"><div className="grid gap-5 xl:grid-cols-[220px_1fr]"><div><ReadinessGauge score={readiness.readiness_score} label={readiness.readiness_label}/>{readiness.score_explanation.length>0&&<div className="mt-4 text-xs leading-5 text-muted"><p className="font-semibold text-ink">Score deductions</p>{readiness.score_explanation.map(x=><p key={x} className="mt-1">{x}</p>)}</div>}</div><div><p className="text-sm font-semibold">Readiness checklist</p><div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">{readiness.checklist.map(item=><div key={item.key} className="rounded-md border border-line bg-white p-3"><div className="flex items-start justify-between gap-2"><p className="text-sm font-semibold">{item.label}</p><StatusBadge status={item.status}/></div><p className="mt-2 text-xs leading-5 text-muted">{item.detail}</p></div>)}</div>{readiness.alternatives.length>0&&<div className="mt-5"><p className="text-sm font-semibold">Database-backed in-network alternatives</p><div className="mt-3 grid gap-3 md:grid-cols-3">{readiness.alternatives.map(a=><div key={a.provider_id} className="rounded-md border border-line bg-white p-3"><p className="font-semibold">{a.provider_name}</p><p className="mt-1 text-xs text-muted">{a.organization_name}</p><p className="mt-2 flex items-center gap-1 text-xs text-muted"><MapPin size={13}/>{a.city}, {a.state} · ZIP3 {a.zip3}</p></div>)}</div></div>}</div></div><div className="mt-5 flex justify-end"><button className="btn-primary" onClick={()=>nav(`/members/${member.member_id}/outreach`)}>Review proactive outreach</button></div></div>}
    </article>})}</div>
  </>
}
