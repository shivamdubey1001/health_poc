import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppProvider } from './context/AppContext'
import ErrorBoundary from './components/ErrorBoundary'
import { AppLayout } from './layouts/AppLayout'
import LandingPage from './pages/LandingPage'
import OverviewPage from './pages/OverviewPage'
import MembersPage from './pages/MembersPage'
import AssessmentResultsPage from './pages/AssessmentResultsPage'
import ReadinessResultsPage from './pages/ReadinessResultsPage'
import MemberIntelligencePage from './pages/MemberIntelligencePage'
import ReadinessPage from './pages/ReadinessPage'
import OutreachPage from './pages/OutreachPage'
import ImpactPage from './pages/ImpactPage'
import SettingsPage from './pages/SettingsPage'
import OutreachQueuePage from './pages/OutreachQueuePage'
import EvaluationPage from './pages/EvaluationPage'

export default function App(){return <ErrorBoundary><AppProvider><BrowserRouter><Routes>
  <Route path="/" element={<LandingPage/>}/>
  <Route element={<AppLayout/>}>
    <Route path="/overview" element={<OverviewPage/>}/>
    <Route path="/members" element={<MembersPage/>}/>
    <Route path="/assessment-results" element={<AssessmentResultsPage/>}/>
    <Route path="/readiness-results" element={<ReadinessResultsPage/>}/>
    <Route path="/queue" element={<Navigate to="/assessment-results" replace/>}/>
    <Route path="/members/:memberId/intelligence" element={<MemberIntelligencePage/>}/>
    <Route path="/members/:memberId/readiness" element={<ReadinessPage/>}/>
    <Route path="/members/:memberId/outreach" element={<OutreachPage/>}/>
    <Route path="/outreach" element={<OutreachQueuePage/>}/>
    <Route path="/evaluation" element={<EvaluationPage/>}/>
    <Route path="/impact" element={<ImpactPage/>}/>
    <Route path="/settings" element={<SettingsPage/>}/>
  </Route>
  <Route path="*" element={<Navigate to="/" replace/>}/>
</Routes></BrowserRouter></AppProvider></ErrorBoundary>}
