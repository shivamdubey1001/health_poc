import { useState } from 'react'
import { AlertCircle, CheckCircle2, Clock, HelpCircle, MapPin } from 'lucide-react'

export type ChecklistLine = {
  key: string; label: string; status: string
  member_status: string; detail: string; is_top_issue: boolean
}
export type MemberOption = { option_id: string; label: string; sublabel: string; kind: string }

const ICON: Record<string, typeof CheckCircle2> = {
  READY: CheckCircle2, IN_PROGRESS: Clock, NEEDS_ATTENTION: AlertCircle, UNKNOWN: HelpCircle,
}
const TONE: Record<string, string> = {
  READY: 'text-emerald-700', IN_PROGRESS: 'text-amber-700',
  NEEDS_ATTENTION: 'text-rose-700', UNKNOWN: 'text-slate-500',
}

/**
 * What the member actually receives.
 *
 * The notification resolves rather than refers. It carries the full readiness
 * checklist and, where the plan already knows the answer, presents a choice the
 * member can act on. A message whose answer is "call an advocate" is a better
 * way of generating the call this product exists to prevent, so the advocate
 * appears only when nothing can be self-resolved.
 */
export function NotificationPreview({
  headline, message, event, score, label, checklist, readyCount, totalItems,
  channel, resolutionMode, callToAction, options, advocateRequired,
}: {
  headline: string; message: string; event: string; score: number; label: string
  checklist: ChecklistLine[]; readyCount: number; totalItems: number; channel: string
  resolutionMode: string; callToAction: string; options: MemberOption[]; advocateRequired: boolean
}) {
  const [chosen, setChosen] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)
  const top = checklist.find(c => c.is_top_issue)
  const rest = checklist.filter(c => !c.is_top_issue)
  const isProviderChoice = options.some(o => o.kind === 'PROVIDER_CHOICE')

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-white">
      <div className="flex items-center justify-between border-b border-line bg-brand-soft/60 px-5 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-brand-dark">
          Member notification preview · {channel}
        </p>
        <span className="rounded-full bg-white px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted">
          {resolutionMode.replaceAll('_', ' ').toLowerCase()}
        </span>
      </div>

      <div className="p-5">
        <h3 className="text-lg font-semibold leading-6">{headline}</h3>
        <p className="mt-2 text-sm leading-6 text-muted">{message}</p>

        <div className="mt-4 flex flex-wrap items-baseline gap-3 rounded-xl border border-line bg-panel px-4 py-3">
          <span className="text-2xl font-bold text-brand-dark">{readyCount}/{totalItems}</span>
          <span className="text-sm text-muted">plan items ready for your {event.toLowerCase()}</span>
          <span className="ml-auto text-xs font-semibold uppercase tracking-wide text-muted">
            {score}% · {label}
          </span>
        </div>

        {/* The action the member can take, in the notification itself. */}
        {options.length > 0 && (
          <fieldset className="mt-5 rounded-xl border-2 border-brand/40 bg-brand-soft/30 p-4">
            <legend className="px-2 text-sm font-semibold text-forest">{callToAction}</legend>
            <div className="mt-2 space-y-2">
              {options.map(opt => (
                <label
                  key={opt.option_id}
                  className={`flex cursor-pointer items-start gap-3 rounded-lg border bg-white p-3 transition ${
                    chosen === opt.option_id ? 'border-brand ring-2 ring-brand/25' : 'border-line hover:border-brand/50'}`}
                >
                  <input
                    type="radio" name="member-choice" className="mt-1"
                    checked={chosen === opt.option_id}
                    onChange={() => { setChosen(opt.option_id); setSubmitted(false) }}
                  />
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold">{opt.label}</span>
                    <span className="mt-0.5 flex items-center gap-1 text-xs text-muted">
                      {isProviderChoice && <MapPin size={12} aria-hidden />}{opt.sublabel}
                    </span>
                  </span>
                </label>
              ))}
            </div>
            <button
              className="btn-primary mt-3 w-full sm:w-auto"
              disabled={!chosen || submitted}
              onClick={() => setSubmitted(true)}
            >
              {submitted ? 'Choice recorded' : 'Confirm my choice'}
            </button>
            {submitted && (
              <p className="mt-2 text-xs leading-5 text-forest">
                In production this updates the member's record and notifies the care team. In the
                prototype it is recorded locally and nothing is sent.
              </p>
            )}
          </fieldset>
        )}

        {options.length === 0 && top && (
          <div className="mt-5 rounded-xl border border-line bg-panel p-4">
            <p className="text-[11px] font-bold uppercase tracking-wide text-muted">In progress</p>
            <p className="mt-1 font-semibold">{top.label}</p>
            <p className="mt-1 text-sm leading-6 text-muted">
              We're confirming this with your provider's office. Nothing is needed from you.
            </p>
          </div>
        )}

        <p className="mt-5 text-sm font-semibold">Your full plan checklist</p>
        <ul className="mt-2 divide-y divide-line rounded-xl border border-line">
          {[...(top ? [top] : []), ...rest].map(item => {
            const Icon = ICON[item.status] || HelpCircle
            return (
              <li key={item.key} className={`flex items-start gap-3 px-4 py-3 ${item.is_top_issue ? 'bg-brand-soft/40' : ''}`}>
                <Icon className={`mt-0.5 shrink-0 ${TONE[item.status] || TONE.UNKNOWN}`} size={17} aria-hidden />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <p className="text-sm font-semibold">{item.label}</p>
                    <span className={`text-xs font-semibold ${TONE[item.status] || TONE.UNKNOWN}`}>
                      {item.member_status}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs leading-5 text-muted">{item.detail}</p>
                </div>
              </li>
            )
          })}
        </ul>

        <p className="mt-4 text-xs leading-5 text-muted">
          {advocateRequired
            ? 'A Member Advocate is offered here because this item has no self-service resolution path.'
            : 'No advocate contact is requested. Everything above is either resolved, being handled for the member, or answerable with one choice.'}
          {' '}Status is conveyed by label as well as colour, and every line comes from a deterministic
          plan, network or authorization lookup rather than from the model.
        </p>
      </div>
    </div>
  )
}
