export function ConfidenceBar({value,label}:{value:number;label:string}){
  const pct=Math.round(value*100); return <div><div className="mb-2 flex items-center justify-between text-sm"><span className="font-medium">{label}</span><span className="font-semibold">{pct}%</span></div><div className="h-2.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-brand" style={{width:`${pct}%`}}/></div></div>
}
