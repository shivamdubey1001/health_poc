import type { ReactNode } from 'react'
export function PageHeader({title,subtitle,action}:{title:string;subtitle:string;action?:ReactNode}){return <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div><h1 className="page-title">{title}</h1><p className="mt-1 max-w-3xl text-sm text-muted">{subtitle}</p></div>{action}</div>}
