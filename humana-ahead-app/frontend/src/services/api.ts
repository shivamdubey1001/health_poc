import type { Member, CareIntent, Readiness, QueueRow, CallRecord, Claim } from '../types/api'

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) }, ...options })
  if (!res.ok) {
    let message = `Request failed: ${res.status}`
    try { const body = await res.json(); message = body?.detail?.message || body?.detail || message } catch { /* noop */ }
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message))
  }
  return res.json()
}

export const api = {
  overview: () => request<any>('/dashboard/overview'),
  members: (search='') => request<Member[]>(`/members?search=${encodeURIComponent(search)}`),
  member: (id:string) => request<Member>(`/members/${id}`),
  context: (id:string) => request<any>(`/members/${id}/context`),
  claims: (id:string) => request<Claim[]>(`/members/${id}/claims`),
  calls: (id:string) => request<CallRecord[]>(`/members/${id}/calls`),
  transcript: (callId:string) => request<any>(`/calls/${callId}/transcript`),
  careIntent: (id:string) => request<CareIntent>(`/members/${id}/care-intent`, { method:'POST' }),
  readiness: (id:string) => request<Readiness>(`/members/${id}/readiness`, { method:'POST' }),
  queue: () => request<QueueRow[]>('/queue/ahead'),
  outreachDraft: (id:string) => request<any>(`/members/${id}/outreach/draft`, { method:'POST' }),
  outreachAction: (id:string, action:'APPROVE'|'REJECT'|'SAVE_FOR_REVIEW', message:string) => request<any>(`/members/${id}/outreach/${action==='APPROVE'?'approve':'reject'}`, { method:'POST', body:JSON.stringify({action,message}) }),
  cost: () => request<any>('/analytics/cost'),
  settings: () => request<any>('/settings'),
  updateSettings: (payload:any) => request<any>('/settings', { method:'PUT', body:JSON.stringify(payload) }),
}
