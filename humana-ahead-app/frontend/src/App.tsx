import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppProvider } from './context/AppContext'
import { AppLayout } from './layouts/AppLayout'
import OverviewPage from './pages/OverviewPage'
import MembersPage from './pages/MembersPage'
import QueuePage from './pages/QueuePage'
import MemberIntelligencePage from './pages/MemberIntelligencePage'
import ReadinessPage from './pages/ReadinessPage'
import OutreachPage from './pages/OutreachPage'
import ImpactPage from './pages/ImpactPage'
import SettingsPage from './pages/SettingsPage'

export default function App(){return <AppProvider><BrowserRouter><Routes><Route element={<AppLayout/>}><Route path="/" element={<OverviewPage/>}/><Route path="/members" element={<MembersPage/>}/><Route path="/queue" element={<QueuePage/>}/><Route path="/members/:memberId/intelligence" element={<MemberIntelligencePage/>}/><Route path="/members/:memberId/readiness" element={<ReadinessPage/>}/><Route path="/members/:memberId/outreach" element={<OutreachPage/>}/><Route path="/impact" element={<ImpactPage/>}/><Route path="/settings" element={<SettingsPage/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Route></Routes></BrowserRouter></AppProvider>}
