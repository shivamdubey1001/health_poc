import { NavLink, Outlet } from 'react-router-dom'
import { BarChart3, ChevronLeft, ChevronRight, ClipboardCheck, FlaskConical, LayoutDashboard, Send, Settings, Sparkles, Users, Menu, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useApp } from '../context/AppContext'
import { api } from '../services/api'
import ErrorBoundary from '../components/ErrorBoundary'
import type { HealthStatus } from '../types/api'

const nav=[
  ['Overview','/overview',LayoutDashboard],
  ['Members','/members',Users],
  ['Scan Results','/assessment-results',Sparkles],
  ['Readiness Results','/readiness-results',ClipboardCheck],
  ['Outreach','/outreach',Send],
  ['Evaluation','/evaluation',FlaskConical],
  ['Impact & Cost','/impact',BarChart3],
  ['Settings','/settings',Settings],
] as const

export function AppLayout(){
  const {collapsed,setCollapsed}=useApp()
  const [mobile,setMobile]=useState(false)
  const [health,setHealth]=useState<HealthStatus|null>(null)
  useEffect(()=>{api.health().then(setHealth).catch(()=>setHealth(null))},[])

  const sidebar=<div className="flex h-full flex-col bg-forest text-white">
    <div className="flex h-16 items-center justify-between border-b border-white/10 px-4">
      <div className={`min-w-0 ${collapsed?'lg:hidden':''}`}><div className="flex items-center gap-2 text-sm font-bold tracking-wide"><span className="h-3 w-3 rounded-full bg-[#7AA83B]"/>Humana Ahead</div><div className="mt-0.5 text-[10px] text-white/60">Proactive care readiness</div></div>
      <button aria-label="Collapse sidebar" className="hidden rounded-md p-2 hover:bg-white/10 lg:block" onClick={()=>setCollapsed(!collapsed)}>{collapsed?<ChevronRight size={18}/>:<ChevronLeft size={18}/>}</button>
      <button aria-label="Close navigation" className="rounded-md p-2 hover:bg-white/10 lg:hidden" onClick={()=>setMobile(false)}><X size={19}/></button>
    </div>
    <nav className="flex-1 space-y-1 p-2">{nav.map(([label,to,Icon])=><NavLink key={label} to={to} onClick={()=>setMobile(false)} className={({isActive})=>`flex min-h-11 items-center gap-3 rounded-md px-3 text-sm font-medium transition ${isActive?'bg-[#5C8727] text-white':'text-white/75 hover:bg-white/10 hover:text-white'} ${collapsed?'lg:justify-center lg:px-0':''}`} title={collapsed?label:undefined}><Icon size={18}/><span className={collapsed?'lg:hidden':''}>{label}</span></NavLink>)}</nav>
    <div className="border-t border-white/10 p-3"><div className={`${collapsed?'lg:hidden':''}`}><p className="text-xs font-semibold text-[#A8CA78]">Synthetic prototype</p><p className="mt-1 text-[11px] leading-4 text-white/55">OpenAI calls occur only after an explicit scan or readiness click.</p></div></div>
  </div>

  return <div className="min-h-screen bg-panel">
    <aside className={`fixed inset-y-0 left-0 z-40 hidden transition-all lg:block ${collapsed?'w-16':'w-64'}`}>{sidebar}</aside>
    {mobile&&<div className="fixed inset-0 z-50 lg:hidden"><button aria-label="Close navigation overlay" className="absolute inset-0 bg-forest/40" onClick={()=>setMobile(false)}/><aside className="relative h-full w-72">{sidebar}</aside></div>}
    <div className={`transition-all ${collapsed?'lg:pl-16':'lg:pl-64'}`}>
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-line bg-white/95 px-4 backdrop-blur sm:px-6">
        <div className="flex items-center gap-3"><button aria-label="Open navigation" className="rounded-md border border-line p-2 lg:hidden" onClick={()=>setMobile(true)}><Menu size={18}/></button><div><p className="text-sm font-semibold">Humana Ahead</p><p className="hidden text-xs text-muted sm:block">Internal Member Advocate prototype</p></div></div>
        <div className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs ${health?.openai_configured?'border-brand/20 bg-brand-soft text-brand-dark':'border-amber-200 bg-amber-50 text-amber-800'}`}><span className={`h-2 w-2 rounded-full ${health?.openai_configured?'bg-brand':'bg-amber-500'}`}/>{health?.openai_configured?`OpenAI ready · ${health.model}`:'API key required'}</div>
      </header>
      <main className="mx-auto max-w-[1500px] p-4 sm:p-6 lg:p-8"><ErrorBoundary><Outlet/></ErrorBoundary></main>
    </div>
  </div>
}
