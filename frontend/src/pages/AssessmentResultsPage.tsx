import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronDown, ChevronUp, ClipboardCheck, RotateCcw } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { StatusBadge } from '../components/StatusBadge'
import { ErrorState } from '../components/ErrorState'
import { api } from '../services/api'
import { useApp } from '../context/AppContext'

export default function AssessmentResultsPage(){
  const {careBatch,setReadinessBatch}=useApp()
  const nav=useNavigate()
  const eligibleIds=useMemo(()=>careBatch?.results.filter(r=>r.assessment.recommended_action==='RUN_READINESS_ASSESSMENT').map(r=>r.member.member_id) ?? [],[careBatch])
  const [selected,setSelected]=useState<string[]>(eligibleIds)
  const [expanded,setExpanded]=useState<string|null>(null)
  const [err,setErr]=useState('')
  const [running,setRunning]=useState(false)
  const selectedSet=useMemo(()=>new Set(selected),[selected])

  if(!careBatch)return <><PageHeader title="Scan Results" subtitle="No Agent 1 assessment has been run in this browser session."/><ErrorState message="Select members on the Members page and click Scan for upcoming procedures first."/><button className="btn-primary mt-4" onClick={()=>nav('/members')}>Go to Members</button></>

  const toggle=(id:string)=>setSelected(selectedSet.has(id)?selected.filter(x=>x!==id):[...selected,id])
  const runReadiness=async()=>{
    if(!selected.length)return
    setRunning(true);setErr('');setReadinessBatch(null)
    try{const result=await api.readinessBatch(selected);setReadinessBatch(result);nav('/readiness-results')}catch(e:any){setErr(e.message)}finally{setRunning(false)}
  }

  return <>
    <PageHeader title="Upcoming care scan" subtitle={`Agent 1 assessed only the ${careBatch.selected_count} members you selected. Readiness has not run yet.`} action={<button className="btn-secondary" onClick={()=>nav('/members')}><RotateCcw size={16}/>Change member selection</button>}/>
    <div className="mb-5 rounded-lg border border-brand/20 bg-brand-soft p-4"><p className="eyebrow">Step 2 · Agent 1 results</p><div className="mt-1 flex flex-wrap items-end justify-between gap-3"><div><p className="text-xl font-semibold">{eligibleIds.length} of {careBatch.selected_count} members crossed the {Math.round(careBatch.threshold*100)}% readiness gate</p><p className="mt-1 text-sm text-muted">Model: {careBatch.model}. Care Intent Confidence is an evidence score, not a calibrated clinical probability.</p></div></div></div>
    {err&&<ErrorState message={err}/>} 
    <div className="space-y-3">{careBatch.results.map(({member,assessment})=>{
      const eligible=assessment.recommended_action==='RUN_READINESS_ASSESSMENT'
      const open=expanded===member.member_id
      return <article key={member.member_id} className="card p-0 overflow-hidden">
        <div className="grid items-center gap-3 p-4 lg:grid-cols-[40px_1.2fr_1.5fr_.7fr_.8fr_.8fr_48px]">
          <div><input className="checkbox" type="checkbox" aria-label={`Select ${member.name} for readiness`} disabled={!eligible} checked={selectedSet.has(member.member_id)} onChange={()=>toggle(member.member_id)}/></div>
          <div><p className="font-semibold">{member.name}</p><p className="text-xs text-muted">{member.member_id} · {member.plan_type}</p></div>
          <div><p className="text-xs font-semibold uppercase tracking-wide text-muted">Likely upcoming care</p><p className="mt-1 font-semibold">{assessment.care_intent.predicted_care_event||'No high-confidence procedure identified'}</p></div>
          <div><p className="text-xs font-semibold uppercase tracking-wide text-muted">Care intent</p><p className="mt-1 text-xl font-bold text-brand-dark">{Math.round(assessment.care_intent.confidence*100)}%</p></div>
          <div><p className="text-xs font-semibold uppercase tracking-wide text-muted">Timing</p><p className="mt-1 text-sm font-medium">{assessment.care_intent.estimated_time_window||'Not inferred'}</p></div>
          <div><p className="text-xs font-semibold uppercase tracking-wide text-muted">Contact risk</p><div className="mt-1"><StatusBadge status={assessment.advocate_contact.risk_level}/></div></div>
          <button className="rounded-md p-2 hover:bg-panel" onClick={()=>setExpanded(open?null:member.member_id)} aria-label="Toggle evidence">{open?<ChevronUp size={18}/>:<ChevronDown size={18}/>}</button>
        </div>
        {open&&<div className="border-t border-line bg-panel/60 p-4"><div className="grid gap-4 lg:grid-cols-2"><div><p className="text-sm font-semibold">Evidence used</p><ul className="mt-2 space-y-2">{assessment.evidence.map((e,i)=><li key={i} className="rounded-md border border-line bg-white p-3 text-sm"><span className="text-[10px] font-bold uppercase tracking-wide text-brand">{e.type.replaceAll('_',' ')}</span><p className="mt-1 leading-5 text-muted">{e.description}</p></li>)}</ul></div><div><p className="text-sm font-semibold">Agent decision</p><div className="mt-2 rounded-md border border-line bg-white p-4"><p className="font-semibold">{eligible?'Eligible for readiness assessment':'Monitor only'}</p><p className="mt-2 text-sm leading-6 text-muted">{assessment.advocate_contact.reason}</p>{assessment.transcript_tool_invoked&&<p className="mt-3 text-xs font-semibold text-brand-dark">A full transcript was retrieved because the Agent Assist summary needed clarification.</p>}</div></div></div></div>}
      </article>
    })}</div>

    <section className="mt-5 flex flex-col gap-3 rounded-lg border border-line bg-white p-4 shadow-soft sm:flex-row sm:items-center sm:justify-between">
      <div><div className="selection-pill">{selected.length} {selected.length===1?'member':'members'} selected for readiness</div><p className="mt-2 text-xs text-muted">Only checked members will invoke Agent 2. Members below the confidence threshold cannot be selected.</p></div>
      <div className="flex flex-wrap gap-2"><button className="btn-secondary" disabled={!eligibleIds.length} onClick={()=>setSelected(selected.length===eligibleIds.length?[]:eligibleIds)}>{selected.length===eligibleIds.length?'Clear eligible':'Select all eligible'}</button><button className="btn-primary min-w-60" disabled={!selected.length||running} onClick={runReadiness}>{running?<><span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"/>Running Agent 2…</>:<><ClipboardCheck size={17}/>Run readiness assessment</>}</button></div>
    </section>
  </>
}
