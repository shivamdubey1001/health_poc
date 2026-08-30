import type { LucideIcon } from 'lucide-react'
export function MetricCard({label,value,detail,Icon}:{label:string;value:string|number;detail?:string;Icon?:LucideIcon}){
  return <div className="card min-w-0"><div className="flex items-start justify-between gap-3"><div><p className="text-sm text-muted">{label}</p><p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>{detail&&<p className="mt-1 text-xs text-muted">{detail}</p>}</div>{Icon&&<div className="rounded-xl bg-brand-soft p-2.5 text-brand"><Icon size={19}/></div>}</div></div>
}
