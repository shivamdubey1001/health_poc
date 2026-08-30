import { createContext, useContext, useState, type ReactNode } from 'react'
import type { CareBatchResult, ReadinessBatchResult } from '../types/api'

type AppState = {
  collapsed:boolean; setCollapsed:(v:boolean)=>void;
  selectedMemberIds:string[]; setSelectedMemberIds:(v:string[])=>void;
  careBatch:CareBatchResult|null; setCareBatch:(v:CareBatchResult|null)=>void;
  readinessBatch:ReadinessBatchResult|null; setReadinessBatch:(v:ReadinessBatchResult|null)=>void;
}

const Ctx = createContext<AppState | null>(null)

function readJson<T>(key:string, fallback:T):T {
  try { const raw=sessionStorage.getItem(key); return raw ? JSON.parse(raw) as T : fallback } catch { return fallback }
}

export function AppProvider({children}:{children:ReactNode}) {
  const [collapsed,setCollapsedState] = useState(() => sessionStorage.getItem('ahead.sidebar') === 'collapsed')
  const [selectedMemberIds,setSelectedState] = useState<string[]>(()=>readJson('ahead.selected', []))
  const [careBatch,setCareBatchState] = useState<CareBatchResult|null>(()=>readJson('ahead.careBatch', null))
  const [readinessBatch,setReadinessBatchState] = useState<ReadinessBatchResult|null>(()=>readJson('ahead.readinessBatch', null))

  const setCollapsed = (v:boolean) => { setCollapsedState(v); sessionStorage.setItem('ahead.sidebar', v?'collapsed':'expanded') }
  const setSelectedMemberIds = (v:string[]) => { setSelectedState(v); sessionStorage.setItem('ahead.selected',JSON.stringify(v)) }
  const setCareBatch = (v:CareBatchResult|null) => { setCareBatchState(v); v ? sessionStorage.setItem('ahead.careBatch',JSON.stringify(v)) : sessionStorage.removeItem('ahead.careBatch') }
  const setReadinessBatch = (v:ReadinessBatchResult|null) => { setReadinessBatchState(v); v ? sessionStorage.setItem('ahead.readinessBatch',JSON.stringify(v)) : sessionStorage.removeItem('ahead.readinessBatch') }

  return <Ctx.Provider value={{collapsed,setCollapsed,selectedMemberIds,setSelectedMemberIds,careBatch,setCareBatch,readinessBatch,setReadinessBatch}}>{children}</Ctx.Provider>
}
export function useApp(){ const v=useContext(Ctx); if(!v) throw new Error('AppProvider missing'); return v }
