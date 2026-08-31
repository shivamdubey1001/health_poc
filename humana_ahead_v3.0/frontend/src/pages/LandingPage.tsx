import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, Database, ShieldCheck } from 'lucide-react'
import { api } from '../services/api'
import type { LandingSummary } from '../types/api'

export default function LandingPage(){
  const [data,setData]=useState<LandingSummary|null>(null)
  const [err,setErr]=useState('')
  const nav=useNavigate()
  useEffect(()=>{api.landing().then(setData).catch(e=>setErr(e.message))},[])
  return <main className="min-h-screen bg-panel px-5 py-10 text-ink sm:px-8 lg:py-14">
    <div className="mx-auto flex max-w-5xl flex-col items-center text-center">
      <div className="flex items-center gap-2 text-base font-bold text-ink"><span className="h-5 w-5 rounded-full bg-brand"/>Humana Ahead</div>
      <h1 className="mt-7 max-w-4xl text-4xl font-bold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
        Find the members with<br className="hidden sm:block"/> something coming — <span className="text-brand">before<br className="hidden sm:block"/> they call.</span>
      </h1>
      <p className="mt-6 max-w-3xl text-base leading-7 text-muted sm:text-lg">
        Ahead brings together plan context, historical claims and recent Member Advocate interactions, then lets an advocate explicitly choose which members to assess for emerging care intent.
      </p>

      {err && <div className="mt-8 w-full max-w-3xl rounded-lg border border-red-200 bg-red-50 p-4 text-left text-sm text-red-700">{err}</div>}
      <div className="mt-8 grid w-full max-w-4xl grid-cols-2 overflow-hidden rounded-lg border border-line bg-white shadow-soft sm:grid-cols-4">
        <Stat value={data?.members ?? '—'} label="Members"/>
        <Stat value={data?.claims_180d ?? '—'} label="Claims 180d"/>
        <Stat value={data?.calls_90d ?? '—'} label="Calls 90d"/>
        <Stat value={data?.authorizations ?? '—'} label="Authorizations" last/>
      </div>

      <button className="btn-primary mt-8 min-w-64 px-7" onClick={()=>nav('/members')}>
        Start my assessment <ArrowRight size={18}/>
      </button>

      <div className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-muted">
        <span className="inline-flex items-center gap-1.5"><Database size={14}/>Synthetic data only</span>
        <span className="inline-flex items-center gap-1.5"><ShieldCheck size={14}/>Human-triggered agent calls</span>
        <span>{data?.openai_configured ? `OpenAI ready · ${data.model}` : 'OpenAI API key not configured yet'}</span>
      </div>
      <p className="mt-2 text-xs text-muted">Data as of {data?.data_as_of ?? '2026-08-29'} · calls summarized over recent interactions · claims retrieved from historical adjudicated data</p>
    </div>
  </main>
}

function Stat({value,label,last=false}:{value:string|number;label:string;last?:boolean}){
  return <div className={`px-3 py-4 sm:py-5 ${last?'':'border-r border-line'} border-b border-line sm:border-b-0`}>
    <div className="text-xl font-bold tracking-wide text-forest sm:text-2xl">{value}</div>
    <div className="mt-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">{label}</div>
  </div>
}
