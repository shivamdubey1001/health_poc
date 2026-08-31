import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { EyeOff, Search, Sparkles, X } from 'lucide-react'
import { api } from '../services/api'
import type { Member } from '../types/api'
import { PageHeader } from '../components/PageHeader'
import { LoadingState } from '../components/LoadingState'
import { ErrorState } from '../components/ErrorState'
import { useApp } from '../context/AppContext'

const guide=[
  ['Member ID','Synthetic identifier used to join enrollment, claims and call history. Names are synthetic and are not sent as the primary model key.'],
  ['Age band','Grouped age range rather than a precise date of birth. It provides high-level context without creating unnecessary precision.'],
  ['Plan','The member’s active synthetic Medicare Advantage plan. Agent 1 sees plan context; Agent 2 later retrieves benefit rules.'],
  ['Claims 90d / 180d','Adjudicated historical claim lines inside the recent windows. The agent receives the relevant claim trajectory, not a future event label.'],
  ['Calls 90d','Member Advocate contacts in the last 90 days. Agent 1 normally receives only the latest 5–6 Agent Assist summaries.'],
  ['Last call topic','The contact-center topic from the most recent advocate call. It is evidence, not a prediction and can be noisy.'],
  ['Authorizations 180d','Existing utilization-management records in the recent window. These are shown here for context but are NOT sent to Agent 1. Agent 2 may retrieve them after the threshold gate.'],
  ['Latest activity','Most recent date across claims, advocate calls or authorization records. It helps an advocate decide which members are worth selecting.'],
]

export default function MembersPage(){
  const [rows,setRows]=useState<Member[]>();const [total,setTotal]=useState(0);const [offset,setOffset]=useState(0);const [notice,setNotice]=useState('');const [candidatesOnly,setCandidatesOnly]=useState(false)
  const [q,setQ]=useState('')
  const [err,setErr]=useState('')
  const [guideOpen,setGuideOpen]=useState(true)
  const [scanning,setScanning]=useState(false)
  const nav=useNavigate()
  const {selectedMemberIds,setSelectedMemberIds,setCareBatch,setReadinessBatch}=useApp()

  useEffect(()=>{const t=setTimeout(()=>api.members(q,50,offset,candidatesOnly).then(p=>{setRows(p.members);setTotal(p.total)}).catch(e=>setErr(e.message)),180);return()=>clearTimeout(t)},[q,offset,candidatesOnly])
  const selectedSet=useMemo(()=>new Set(selectedMemberIds),[selectedMemberIds])
  const visibleIds=rows?.map(x=>x.member_id) ?? []

  const toggle=(id:string)=>{
    if(selectedSet.has(id)) setSelectedMemberIds(selectedMemberIds.filter(x=>x!==id))
    else {
      if(selectedMemberIds.length>=25){setNotice('Prototype safeguard: 25 members maximum per scan, to control API cost and latency.');return}
      setSelectedMemberIds([...selectedMemberIds,id])
    }
  }
  const selectVisible=()=>{
    const merged=Array.from(new Set([...selectedMemberIds,...visibleIds])).slice(0,25)
    setSelectedMemberIds(merged)
    if(visibleIds.length>25)setNotice('Selected the first 25 visible members. The prototype batch safeguard is 25 members per scan.')
  }
  const runScan=async()=>{
    if(!selectedMemberIds.length)return
    setScanning(true);setErr('');setCareBatch(null);setReadinessBatch(null)
    try{
      const result=await api.careIntentBatch(selectedMemberIds)
      setCareBatch(result)
      nav('/assessment-results')
    }catch(e:any){setErr(e.message)}finally{setScanning(false)}
  }

  return <>
    <PageHeader title="Members" subtitle="Select exactly which members Agent 1 should evaluate. Merely opening this page makes no LLM call." action={<div className="relative w-full sm:w-80"><Search className="absolute left-3 top-3.5 text-muted" size={17}/><input className="input pl-9" placeholder="Search name or member ID" value={q} onChange={e=>setQ(e.target.value)}/></div>}/>

    <section className="mb-5 overflow-hidden rounded-lg border border-line bg-white shadow-soft">
      <div className="flex items-center justify-between bg-brand-soft px-5 py-3"><div><p className="text-sm font-bold text-forest">What you’re looking at</p><p className="mt-0.5 text-xs text-muted">Field guide for the member table</p></div><button className="inline-flex items-center gap-2 text-sm font-semibold text-brand-dark" onClick={()=>setGuideOpen(!guideOpen)}>{guideOpen?<><EyeOff size={16}/>Hide field guide</>:<>Show field guide</>}</button></div>
      {guideOpen&&<div className="grid sm:grid-cols-2 xl:grid-cols-4">{guide.map(([title,copy])=><div key={title} className="border-b border-r border-line p-4 last:border-r-0"><p className="text-sm font-bold text-ink">{title}</p><p className="mt-1 text-xs leading-5 text-muted">{copy}</p></div>)}</div>}
    </section>

    {err&&<div role="alert" className="mb-4 flex items-start justify-between gap-4 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900"><span>{err}</span><button aria-label="Dismiss error" onClick={()=>setErr('')}><X size={17}/></button></div>}
    {notice&&<div role="status" className="mb-4 flex items-start justify-between gap-4 rounded-lg border border-line bg-panel p-4 text-sm text-ink"><span>{notice}</span><button aria-label="Dismiss notice" onClick={()=>setNotice('')}><X size={17}/></button></div>}

    {!rows?<LoadingState label="Loading synthetic members…"/>:<div className="card overflow-hidden p-0">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-3">
        <div>
          <p className="text-sm font-semibold">Showing {rows.length} of {total}{candidatesOnly?' with recent activity':' members'}</p>
          <p className="text-xs text-muted">Checkbox selection controls which records are sent to Agent 1.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <label className="inline-flex items-center gap-2 rounded-lg border border-line px-3 py-1.5 text-sm">
            <input type="checkbox" className="checkbox" checked={candidatesOnly} onChange={e=>{setOffset(0);setCandidatesOnly(e.target.checked)}}/>
            <span title="The deterministic Tier-0 filter: a call or claim in the last 45 days, or an open follow-up. No model call is involved.">Recent activity only</span>
          </label>
          <button className="btn-secondary min-h-9 py-1.5" onClick={selectVisible}>Select visible</button>
          <button className="btn-secondary min-h-9 py-1.5" disabled={!selectedMemberIds.length} onClick={()=>setSelectedMemberIds([])}>Clear selection</button>
        </div>
      </div>
      <div className="max-h-[590px] overflow-auto"><table className="w-full min-w-[1180px] text-left text-sm"><thead className="sticky top-0 z-10 bg-panel text-xs uppercase tracking-wide text-muted"><tr><th className="px-4 py-3"><span className="sr-only">Select</span></th><th className="px-4 py-3">Member</th><th className="px-4 py-3">Age band</th><th className="px-4 py-3">Plan</th><th className="px-4 py-3">Claims 90d / 180d</th><th className="px-4 py-3">Calls 90d</th><th className="px-4 py-3">Last call topic</th><th className="px-4 py-3">Auth 180d</th><th className="px-4 py-3">Latest activity</th></tr></thead>
      <tbody className="divide-y divide-line">{rows.map(m=>{const checked=selectedSet.has(m.member_id);return <tr key={m.member_id} className={checked?'bg-brand-soft/60':'hover:bg-panel'}><td className="px-4 py-4"><input aria-label={`Select ${m.name}`} className="checkbox" type="checkbox" checked={checked} onChange={()=>toggle(m.member_id)}/></td><td className="px-4 py-4"><p className="font-semibold">{m.name}</p><p className="text-xs text-muted">{m.member_id} · {m.county} County</p></td><td className="px-4 py-4">{m.age_band}</td><td className="px-4 py-4"><p className="max-w-56 font-medium">{m.plan_name}</p><p className="text-xs text-muted">{m.plan_type}</p></td><td className="px-4 py-4"><span className="font-semibold">{m.claims_90d}</span> / {m.claims_180d}</td><td className="px-4 py-4">{m.calls_90d}</td><td className="px-4 py-4"><span className="block max-w-48 truncate" title={m.last_call_topic||''}>{m.last_call_topic||'No prior call'}</span>{m.last_call_follow_up_required&&<span className="mt-1 inline-block rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-800">FOLLOW-UP</span>}</td><td className="px-4 py-4">{m.authorization_count_180d}</td><td className="px-4 py-4">{m.latest_activity_date||'—'}</td></tr>})}</tbody></table></div>
      <div className="flex items-center justify-between border-t border-line px-5 py-3">
        <p className="text-xs text-muted">Rows {total===0?0:offset+1}–{Math.min(offset+50,total)} of {total}</p>
        <div className="flex gap-2">
          <button className="btn-secondary min-h-9 py-1.5" disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-50))}>Previous</button>
          <button className="btn-secondary min-h-9 py-1.5" disabled={offset+50>=total} onClick={()=>setOffset(offset+50)}>Next</button>
        </div>
      </div>
    </div>}

    <section className="mt-5 flex flex-col gap-3 rounded-lg border border-line bg-white p-4 shadow-soft sm:flex-row sm:items-center sm:justify-between">
      <div><div className="selection-pill">{selectedMemberIds.length} {selectedMemberIds.length===1?'member':'members'} selected</div><p className="mt-2 text-xs text-muted">Only these members will be sent to Agent 1. Maximum 25 per prototype batch.</p></div>
      <button className="btn-primary min-w-64" aria-busy={scanning} disabled={!selectedMemberIds.length||scanning} onClick={runScan}>{scanning?<><span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"/>Scanning {selectedMemberIds.length} members concurrently…</>:<><Sparkles size={17}/>Scan for upcoming procedures</>}</button>
    </section>
  </>
}
