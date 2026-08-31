import type { Member, CareIntent, Readiness, QueueRow, CallRecord, Claim, LandingSummary, HealthStatus, CareBatchResult, ReadinessBatchResult, MemberPage, EvalLabels, BacktestResult, PerturbationResult, DecisionStats, OutreachDraft } from '../types/api'

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) }, ...options })
  if (!res.ok) {
    let message = `Request failed: ${res.status}`
    try {
      const body = await res.json()
      message = body?.detail?.message || body?.detail || message
    } catch { /* noop */ }
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message))
  }
  return res.json()
}

export const api = {
  health: () => request<HealthStatus>('/health'),
  landing: () => request<LandingSummary>('/landing/summary'),
  overview: () => request<any>('/dashboard/overview'),
  members: (search='', limit=50, offset=0, candidatesOnly=false) =>
    request<MemberPage>(`/members?search=${encodeURIComponent(search)}&limit=${limit}&offset=${offset}&candidates_only=${candidatesOnly}`),
  member: (id:string) => request<Member>(`/members/${id}`),
  context: (id:string) => request<any>(`/members/${id}/context`),
  claims: (id:string) => request<Claim[]>(`/members/${id}/claims`),
  calls: (id:string) => request<CallRecord[]>(`/members/${id}/calls`),
  transcript: (callId:string) => request<any>(`/calls/${callId}/transcript`),
  careIntent: (id:string) => request<CareIntent>(`/members/${id}/care-intent`, { method:'POST' }),
  latestCareIntent: (id:string) => request<CareIntent>(`/members/${id}/care-intent/latest`),
  careIntentBatch: (memberIds:string[]) => request<CareBatchResult>('/assessments/care-intent', { method:'POST', body:JSON.stringify({member_ids:memberIds}) }),
  readiness: (id:string) => request<Readiness>(`/members/${id}/readiness`, { method:'POST' }),
  latestReadiness: (id:string) => request<Readiness>(`/members/${id}/readiness/latest`),
  readinessBatch: (memberIds:string[]) => request<ReadinessBatchResult>('/assessments/readiness', { method:'POST', body:JSON.stringify({member_ids:memberIds}) }),
  queue: () => request<QueueRow[]>('/queue/ahead'),
  outreachDraft: (id:string) => request<OutreachDraft>(`/members/${id}/outreach/draft`, { method:'POST' }),
  // Single decision endpoint. Routing SAVE_FOR_REVIEW to /reject meant any
  // endpoint-level metric counted saves as rejections, and override rate by
  // action is exactly the data this product needs.
  outreachAction: (id:string, action:'APPROVE'|'REJECT'|'SAVE_FOR_REVIEW', message:string, originalMessage='') =>
    request<any>(`/members/${id}/outreach/decision`, { method:'POST', body:JSON.stringify({action, message, original_message:originalMessage}) }),
  decisionStats: () => request<DecisionStats>('/outreach/decisions/stats'),
  evalLabels: () => request<EvalLabels>('/eval/labels'),
  backtest: (limit=20, threshold?:number, indexDate?:string) =>
    request<BacktestResult>('/eval/backtest', { method:'POST', body:JSON.stringify({limit, threshold, index_date:indexDate}) }),
  evalRuns: () => request<any[]>('/eval/runs'),
  perturbation: (memberId:string) =>
    request<PerturbationResult>('/eval/perturbation', { method:'POST', body:JSON.stringify({member_id:memberId}) }),
  consistency: (memberId:string, runs=3) =>
    request<any>(`/eval/consistency?member_id=${encodeURIComponent(memberId)}&runs_count=${runs}`, { method:'POST' }),
  cost: () => request<any>('/analytics/cost'),
  settings: () => request<any>('/settings'),
  updateSettings: (payload:any) => request<any>('/settings', { method:'PUT', body:JSON.stringify(payload) }),
}
