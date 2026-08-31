import { createContext, useContext, useState, type ReactNode } from 'react'
import type { CareBatchResult, ReadinessBatchResult } from '../types/api'

type AppState = {
  collapsed:boolean; setCollapsed:(v:boolean)=>void;
  selectedMemberIds:string[]; setSelectedMemberIds:(v:string[])=>void;
  careBatch:CareBatchResult|null; setCareBatch:(v:CareBatchResult|null)=>void;
  readinessBatch:ReadinessBatchResult|null; setReadinessBatch:(v:ReadinessBatchResult|null)=>void;
}

const Ctx = createContext<AppState | null>(null)

/**
 * Assessment results are held in memory only.
 *
 * They were previously written to sessionStorage, which left inferred clinical
 * content - predicted procedures and confidence scores for named members - in
 * browser storage on what may be a shared advocate workstation. The backend now
 * persists results, so navigation can re-fetch them instead. Only non-clinical
 * UI preferences are stored client-side.
 */
function readPreference<T>(key:string, fallback:T):T {
  try { const raw = sessionStorage.getItem(key); return raw ? JSON.parse(raw) as T : fallback }
  catch { return fallback }
}

export function AppProvider({children}:{children:ReactNode}) {
  const [collapsed,setCollapsedState] = useState(() => sessionStorage.getItem('ahead.sidebar') === 'collapsed')
  // Member IDs are pseudonymous selection state, not clinical content.
  const [selectedMemberIds,setSelectedState] = useState<string[]>(()=>readPreference('ahead.selected', []))
  const [careBatch,setCareBatch] = useState<CareBatchResult|null>(null)
  const [readinessBatch,setReadinessBatch] = useState<ReadinessBatchResult|null>(null)

  const setCollapsed = (v:boolean) => { setCollapsedState(v); sessionStorage.setItem('ahead.sidebar', v?'collapsed':'expanded') }
  const setSelectedMemberIds = (v:string[]) => { setSelectedState(v); sessionStorage.setItem('ahead.selected',JSON.stringify(v)) }

  return <Ctx.Provider value={{collapsed,setCollapsed,selectedMemberIds,setSelectedMemberIds,careBatch,setCareBatch,readinessBatch,setReadinessBatch}}>{children}</Ctx.Provider>
}

export function useApp(){ const v=useContext(Ctx); if(!v) throw new Error('AppProvider missing'); return v }
