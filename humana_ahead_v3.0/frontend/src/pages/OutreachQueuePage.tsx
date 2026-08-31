import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, Edit3, Send, ShieldCheck, XCircle } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { LoadingState } from '../components/LoadingState'
import { ErrorState } from '../components/ErrorState'
import { api } from '../services/api'
import type { OutreachDraft, QueueRow } from '../types/api'
import { NotificationPreview } from '../components/NotificationPreview'

type DraftState = {
  message: string
  original: string
  channel: string
  messageClass: string
  draft?: OutreachDraft
  loading: boolean
  result?: { status: string; message: string; was_edited?: boolean }
  error?: string
}

const CLASS_LABEL: Record<string, string> = {
  INFORMATIONAL: 'Informational',
  BENEFIT_SURFACING: 'Benefit surfacing',
  COST_DISCLOSURE: 'Cost disclosure',
  CARE_REDIRECTION: 'Care redirection',
  CLINICAL_ADJACENT: 'Clinical adjacent',
}

export default function OutreachQueuePage() {
  const nav = useNavigate()
  const [rows, setRows] = useState<QueueRow[]>()
  const [names, setNames] = useState<Record<string, string>>({})
  const [drafts, setDrafts] = useState<Record<string, DraftState>>({})
  const [err, setErr] = useState('')

  useEffect(() => {
    api.queue()
      .then(async q => {
        const ready = q.filter(r => r.readiness !== null && r.readiness !== undefined)
        setRows(ready)
        const entries = await Promise.all(ready.map(async r => {
          try { const m = await api.member(r.member_id); return [r.member_id, m.name] as const }
          catch { return [r.member_id, r.member_id] as const }
        }))
        setNames(Object.fromEntries(entries))
      })
      .catch(e => setErr(e.message))
  }, [])

  const loadDraft = async (memberId: string) => {
    setDrafts(d => ({ ...d, [memberId]: { message: '', original: '', channel: '', messageClass: '', loading: true } }))
    try {
      const draft = await api.outreachDraft(memberId)
      setDrafts(d => ({ ...d, [memberId]: {
        message: draft.message, original: draft.message,
        channel: draft.channel, messageClass: draft.message_class || 'INFORMATIONAL',
        draft, loading: false,
      }}))
    } catch (e: any) {
      setDrafts(d => ({ ...d, [memberId]: { message: '', original: '', channel: '', messageClass: '', loading: false, error: e.message } }))
    }
  }

  const act = async (memberId: string, action: 'APPROVE' | 'SAVE_FOR_REVIEW' | 'REJECT') => {
    const draft = drafts[memberId]
    if (!draft) return
    try {
      const result = await api.outreachAction(memberId, action, draft.message, draft.original)
      setDrafts(d => ({ ...d, [memberId]: { ...d[memberId], result } }))
    } catch (e: any) {
      setDrafts(d => ({ ...d, [memberId]: { ...d[memberId], error: e.message } }))
    }
  }

  if (err) return <><PageHeader title="Proactive Outreach" subtitle="Advocate review queue." /><ErrorState message={err} /></>
  if (!rows) return <><PageHeader title="Proactive Outreach" subtitle="Advocate review queue." /><LoadingState label="Loading the outreach queue…" /></>

  return (
    <>
      <PageHeader
        title="Proactive Outreach"
        subtitle="Ahead drafts administrative outreach. A Member Advocate remains the decision-maker, and Prototype Mode never sends a real message."
      />

      <div className="mb-5 flex items-start gap-3 rounded-lg border border-brand/20 bg-brand-soft p-4">
        <ShieldCheck className="mt-0.5 shrink-0 text-brand-dark" size={20} />
        <div>
          <p className="text-sm font-semibold text-forest">Human approval is required for every message class</p>
          <p className="mt-1 text-sm leading-6 text-muted">
            Governance is applied per message class, not per confidence level. A reassurance message is
            low consequence at any confidence; a message asking a member to change provider is high
            consequence at any confidence. Approve, edit and reject rates by class are recorded, and are
            what would eventually justify automating the lowest-risk classes.
          </p>
        </div>
      </div>

      {rows.length === 0 && (
        <>
          <ErrorState message="No members have completed a readiness assessment yet. Run Agent 1, then Agent 2, and they will appear here for review." />
          <button className="btn-primary mt-4" onClick={() => nav('/members')}>Go to Members</button>
        </>
      )}

      <div className="space-y-4">
        {rows.map(row => {
          const draft = drafts[row.member_id]
          return (
            <article key={row.member_id} className="card">
              {/* Fixed grid rather than justify-between: variable-length member
                  names were pushing the readiness and issue columns to a
                  different horizontal position on every row. */}
              <div className="grid items-center gap-4 sm:grid-cols-[minmax(0,1.4fr)_96px_minmax(0,1.4fr)_auto]">
                <div className="min-w-0">
                  <p className="truncate font-semibold">{names[row.member_id] || row.member_id}</p>
                  <p className="truncate text-xs text-muted">{row.member_id} · {row.predicted_care_event}</p>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted">Readiness</p>
                  <p className="mt-1 text-xl font-bold text-brand-dark">{row.readiness}%</p>
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted">Top issue</p>
                  <p className="mt-1 truncate font-semibold">{row.top_issue || '—'}</p>
                </div>
                <div className="justify-self-start sm:justify-self-end">
                  {!draft && (
                    <button className="btn-primary whitespace-nowrap" onClick={() => loadDraft(row.member_id)}>
                      <Edit3 size={16} />Draft outreach
                    </button>
                  )}
                </div>
              </div>

              {draft?.loading && <div className="mt-4"><LoadingState label="Generating draft…" /></div>}
              {draft?.error && <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800" role="alert">{draft.error}</p>}

              {draft && !draft.loading && !draft.error && (
                <div className="mt-4 grid gap-4 xl:grid-cols-3">
                  <div className="xl:col-span-2">
                    <p className="eyebrow">Generated outreach draft</p>
                    <textarea
                      className="mt-2 min-h-36 w-full rounded-xl border border-line p-4 text-base leading-7"
                      value={draft.message}
                      aria-label={`Outreach message for ${names[row.member_id] || row.member_id}`}
                      onChange={e => setDrafts(d => ({ ...d, [row.member_id]: { ...d[row.member_id], message: e.target.value } }))}
                    />
                    <p className="mt-2 text-xs text-muted">
                      Channel preference: {draft.channel}. Message class:{' '}
                      <span className="font-semibold">{CLASS_LABEL[draft.messageClass] || draft.messageClass}</span>.
                      {draft.message.trim() !== draft.original.trim() &&
                        <span className="ml-1 font-semibold text-amber-800">Edited — the change is recorded.</span>}
                    </p>
                  </div>

                  {draft.draft?.checklist && draft.draft.checklist.length > 0 && (
                    <div className="xl:col-span-2">
                      <NotificationPreview
                        headline={draft.draft.headline || ''} message={draft.message}
                        event={draft.draft.predicted_care_event || ''}
                        score={draft.draft.readiness_score || 0} label={draft.draft.readiness_label || ''}
                        checklist={draft.draft.checklist}
                        readyCount={draft.draft.ready_count || 0} totalItems={draft.draft.total_items || 0}
                        channel={draft.channel} resolutionMode={draft.draft.resolution_mode || 'NO_ACTION'}
                        callToAction={draft.draft.call_to_action || ''}
                        options={draft.draft.member_options || []}
                        advocateRequired={!!draft.draft.advocate_required}
                      />
                    </div>
                  )}

                  <div className="space-y-2">
                    <button className="btn-primary w-full" disabled={!!draft.result} onClick={() => act(row.member_id, 'APPROVE')}>
                      <Send size={16} />Approve &amp; Send
                    </button>
                    <button className="btn-secondary w-full" disabled={!!draft.result} onClick={() => act(row.member_id, 'SAVE_FOR_REVIEW')}>
                      Save for Review
                    </button>
                    <button className="btn-secondary w-full text-rose-700" disabled={!!draft.result} onClick={() => act(row.member_id, 'REJECT')}>
                      <XCircle size={16} />Do Not Contact
                    </button>
                    <button className="btn-secondary w-full" onClick={() => nav(`/members/${row.member_id}/outreach`)}>
                      Open full member view
                    </button>
                  </div>
                </div>
              )}

              {draft?.result && (
                <div className="mt-4 flex gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4" role="status">
                  <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-700" size={20} />
                  <div>
                    <p className="font-semibold text-emerald-800">{draft.result.status.replaceAll('_', ' ')}</p>
                    <p className="mt-1 text-sm text-emerald-700">{draft.result.message}</p>
                  </div>
                </div>
              )}
            </article>
          )
        })}
      </div>
    </>
  )
}
