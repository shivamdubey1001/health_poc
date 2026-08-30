const styles:Record<string,string> = {
  READY:'bg-emerald-50 text-emerald-700 border-emerald-200',
  NEEDS_ATTENTION:'bg-rose-50 text-rose-700 border-rose-200',
  IN_PROGRESS:'bg-amber-50 text-amber-700 border-amber-200',
  UNKNOWN:'bg-slate-100 text-slate-700 border-slate-200',
  NOT_APPLICABLE:'bg-slate-50 text-slate-500 border-slate-200',
  HIGH:'bg-rose-50 text-rose-700 border-rose-200', MEDIUM:'bg-amber-50 text-amber-700 border-amber-200', LOW:'bg-emerald-50 text-emerald-700 border-emerald-200',
}
export function StatusBadge({status}:{status:string}){
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${styles[status] || styles.UNKNOWN}`}>{status.replaceAll('_',' ')}</span>
}
