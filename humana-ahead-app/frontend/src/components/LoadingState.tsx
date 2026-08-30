import { LoaderCircle } from 'lucide-react'
export function LoadingState({label='Loading…'}:{label?:string}){return <div className="card flex items-center gap-3 text-sm text-muted"><LoaderCircle className="animate-spin" size={18}/>{label}</div>}
