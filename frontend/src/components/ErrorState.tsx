import { CircleAlert } from 'lucide-react'
export function ErrorState({message}:{message:string}){return <div className="card border-rose-200 bg-rose-50"><div className="flex gap-3"><CircleAlert className="mt-0.5 text-rose-600" size={18}/><div><p className="font-semibold text-rose-800">Something needs attention</p><p className="mt-1 text-sm text-rose-700">{message}</p></div></div></div>}
