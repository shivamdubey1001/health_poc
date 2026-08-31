import { useEffect,useState } from 'react'
import { BrainCircuit, CircleDollarSign, Clock3, FileText, Workflow } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../services/api'
import { PageHeader } from '../components/PageHeader'
import { MetricCard } from '../components/MetricCard'
import { LoadingState } from '../components/LoadingState'
import { ErrorState } from '../components/ErrorState'

export default function ImpactPage(){
  const [d,setD]=useState<any>();const [err,setErr]=useState('')
  useEffect(()=>{api.cost().then(setD).catch(e=>setErr(e.message))},[])
  if(err)return <ErrorState message={err}/>;if(!d)return <LoadingState/>
  return <><PageHeader title="Impact & Cost" subtitle="This page reports measured prototype AI usage only. It does not invent call savings, labor savings or ROI."/><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><MetricCard label="Agent 1 calls" value={d.agent1_calls} Icon={BrainCircuit}/><MetricCard label="Agent 2 calls" value={d.agent2_calls} Icon={Workflow}/><MetricCard label="Input tokens" value={d.total_input_tokens.toLocaleString()} Icon={FileText}/><MetricCard label="Output tokens" value={d.total_output_tokens.toLocaleString()}/><MetricCard label="Estimated AI cost" value={`$${Number(d.estimated_ai_cost).toFixed(4)}`} detail={d.model} Icon={CircleDollarSign}/><MetricCard label="Cost / member evaluated" value={`$${Number(d.cost_per_member_evaluated).toFixed(4)}`}/><MetricCard label="Transcript fallbacks" value={d.transcript_tool_invocations}/><MetricCard label="Average AI latency" value={`${d.average_latency_ms} ms`} Icon={Clock3}/></div><div className="mt-6 grid gap-5 xl:grid-cols-5"><section className="card xl:col-span-3"><p className="eyebrow">Actual prototype funnel</p><h2 className="section-title mt-1">Model calls made in this running backend session</h2><div className="mt-5 h-64"><ResponsiveContainer width="100%" height="100%"><BarChart data={d.funnel} layout="vertical"><CartesianGrid strokeDasharray="3 3" horizontal={false}/><XAxis type="number"/><YAxis type="category" dataKey="label" width={150} tick={{fontSize:12}}/><Tooltip/><Bar dataKey="value" fill="#5C8727" radius={[0,8,8,0]}/></BarChart></ResponsiveContainer></div></section><section className="card xl:col-span-2"><p className="eyebrow">Business-value guardrail</p><h2 className="section-title mt-1">Do not claim profitability before a pilot</h2><p className="mt-4 text-sm leading-6 text-muted">{d.business_value_note}</p><div className="mt-5 rounded-lg bg-panel p-4 text-xs leading-5 text-muted">{d.pricing_note}</div></section></div></>
}
