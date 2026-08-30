import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

const Ctx = createContext<{collapsed:boolean; setCollapsed:(v:boolean)=>void} | null>(null)

export function AppProvider({children}:{children:ReactNode}) {
  const [collapsed,setCollapsedState] = useState(() => sessionStorage.getItem('ahead.sidebar') === 'collapsed')
  const setCollapsed = (v:boolean) => { setCollapsedState(v); sessionStorage.setItem('ahead.sidebar', v?'collapsed':'expanded') }
  return <Ctx.Provider value={{collapsed,setCollapsed}}>{children}</Ctx.Provider>
}
export function useApp(){ const v=useContext(Ctx); if(!v) throw new Error('AppProvider missing'); return v }
