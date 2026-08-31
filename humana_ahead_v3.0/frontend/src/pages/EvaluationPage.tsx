import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, FlaskConical, Play, Target } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { LoadingState } from '../components/LoadingState'
import { api } from '../services/api'
import type { BacktestResult, EvalLabels, PerturbationResult } from '../types/api'

const pct = (v: number) => `${Math.round(v * 100)}%`

export default function EvaluationPage() {
  const [labels, setLabels] = useState<EvalLabels>()
  const [result, setResult] = useState<BacktestResult>()
  const [perturb, setPerturb] = useState<PerturbationResult>()
  const [running, setRunning] = useState<'' | 'backtest' | 'perturb'>('')
  const [err, setErr] = useState('')
  const [size, setSize] = useState(20)
  const [member, setMember] = useState('M0001')

  useEffect(() => { api.evalLabels().then(setLabels).catch(e => setErr(e.message)) }, [])

  const runBacktest = async () => {
    setErr(''); setRunning('backtest')
    try { setResult(await api.backtest(size)) }
    catch (e: any) { setErr(e.message) }
    finally { setRunning('') }
  }

  const runPerturbation = async () => {
    setErr(''); setRunning('perturb')
    try { setPerturb(await api.perturbation(member)) }
    catch (e: any) { setErr(e.message) }
    finally { setRunning('') }
  }

  return (
    <>
      <PageHeader
        title="Evaluation"
        subtitle="The outcome label lags by roughly ninety days, so waiting for claims is not an acceptable answer on day one. These checks work today."
      />

      {err && (
        <div className="mb-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert">
          {err}
        </div>
      )}

      {/* ---------------------------------------------------------- labels */}
      <section className="card mb-5">
        <p className="eyebrow">Held-out labels</p>
        <h2 className="section-title mt-1">Where the ground truth comes from</h2>
        {!labels ? <LoadingState label="Deriving labels…" /> : (
          <>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              {[
                ['Upcoming procedure', labels.by_label.UPCOMING_PROCEDURE ?? 0, 'text-brand-dark'],
                ['No evidence', labels.by_label.NO_EVIDENCE ?? 0, 'text-slate-700'],
                ['Ambiguous (excluded)', labels.by_label.AMBIGUOUS ?? 0, 'text-amber-800'],
              ].map(([label, value, tone]) => (
                <div key={String(label)} className="rounded-xl border border-line bg-panel p-4">
                  <p className={`text-2xl font-bold ${tone}`}>{value as number}</p>
                  <p className="mt-1 text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 rounded-xl border border-brand-soft bg-brand-soft/40 p-4">
              <p className="text-sm leading-6"><span className="font-semibold">Method. </span>{labels.method}</p>
              <p className="mt-2 text-sm leading-6"><span className="font-semibold">Known limitation. </span>{labels.limitation}</p>
            </div>
          </>
        )}
      </section>

      {/* -------------------------------------------------------- backtest */}
      <section className="card mb-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="eyebrow">Retrospective backtest</p>
            <h2 className="section-title mt-1">Precision and recall, available today</h2>
            <p className="mt-2 max-w-prose text-sm leading-6 text-muted">
              Agent 1 is scored against labels derived from prior-authorization records, which its
              system prompt forbids it from reading. Members are stratified so a small run contains
              both positives and negatives.
            </p>
          </div>
          <div className="flex items-end gap-2">
            <label className="text-sm">
              <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted">Members</span>
              <input
                type="number" min={4} max={60} value={size}
                onChange={e => setSize(Math.max(4, Math.min(60, Number(e.target.value) || 20)))}
                className="w-24 rounded-lg border border-line px-3 py-2"
                aria-label="Number of members to score"
              />
            </label>
            <button className="btn-primary" onClick={runBacktest} disabled={running !== ''}>
              {running === 'backtest'
                ? <><span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />Scoring…</>
                : <><Play size={16} />Run backtest</>}
            </button>
          </div>
        </div>

        {running === 'backtest' && (
          <p className="mt-4 text-sm text-muted" aria-live="polite">
            Assessing {size} members. Each is a real model call, so this takes a moment.
          </p>
        )}

        {result && (
          <div className="mt-5">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ['Precision', pct(result.scored.precision)],
                ['Recall', pct(result.scored.recall)],
                ['F1', result.scored.f1.toFixed(2)],
                ['Groundedness', pct(result.mean_groundedness)],
              ].map(([k, v]) => (
                <div key={k} className="rounded-xl border border-line bg-panel p-4">
                  <p className="text-3xl font-bold text-brand-dark">{v}</p>
                  <p className="mt-1 text-xs font-medium uppercase tracking-wide text-muted">{k}</p>
                </div>
              ))}
            </div>

            <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-4">
              {[
                ['True positives', result.scored.true_positives],
                ['False positives', result.scored.false_positives],
                ['Missed', result.scored.false_negatives],
                ['Excluded as ambiguous', result.scored.excluded_ambiguous],
              ].map(([k, v]) => (
                <div key={String(k)} className="flex items-baseline justify-between rounded-lg border border-line px-3 py-2">
                  <dt className="text-muted">{k}</dt><dd className="font-semibold">{v as number}</dd>
                </div>
              ))}
            </dl>

            <p className="mt-3 rounded-xl border border-line bg-panel p-4 text-sm leading-6 text-muted">
              {result.scored.interpretation}
            </p>

            <h3 className="mt-6 text-sm font-semibold">Threshold sweep</h3>
            <p className="mt-1 text-sm text-muted">
              Where the gate sits is a product decision, not a default. This is the curve that decision
              should be made on.
            </p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[520px] text-sm">
                <thead className="bg-panel text-left text-xs uppercase tracking-wide text-muted">
                  <tr>
                    <th scope="col" className="px-3 py-2">Threshold</th>
                    <th scope="col" className="px-3 py-2">Precision</th>
                    <th scope="col" className="px-3 py-2">Recall</th>
                    <th scope="col" className="px-3 py-2">F1</th>
                    <th scope="col" className="px-3 py-2">Flagged</th>
                    <th scope="col" className="px-3 py-2">Missed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {result.threshold_sweep.map(r => (
                    <tr key={r.threshold} className={r.threshold === result.scored.threshold ? 'bg-brand-soft/50 font-semibold' : ''}>
                      <td className="px-3 py-2">{r.threshold.toFixed(2)}</td>
                      <td className="px-3 py-2">{pct(r.precision)}</td>
                      <td className="px-3 py-2">{pct(r.recall)}</td>
                      <td className="px-3 py-2">{r.f1.toFixed(2)}</td>
                      <td className="px-3 py-2">{r.true_positives + r.false_positives}</td>
                      <td className="px-3 py-2">{r.false_negatives}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {result.scored.misses.length > 0 && (
              <>
                <h3 className="mt-6 text-sm font-semibold">Missed members</h3>
                <ul className="mt-2 space-y-1 text-sm text-muted">
                  {result.scored.misses.map(m => (
                    <li key={m.member_id}>
                      <span className="font-mono">{m.member_id}</span> — {m.actual}, {m.days_out} days out,
                      scored {m.confidence.toFixed(2)}
                    </li>
                  ))}
                </ul>
              </>
            )}

            <p className="mt-4 text-xs text-muted">
              Model {result.model} · prompt {result.prompt_version} · index date {result.index_date}
              {result.failed > 0 && ` · ${result.failed} assessment(s) failed`}
            </p>
          </div>
        )}
      </section>

      {/* ----------------------------------------------------- perturbation */}
      <section className="card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="eyebrow">Label-free check</p>
            <h2 className="section-title mt-1">Does confidence respond to evidence?</h2>
            <p className="mt-2 max-w-prose text-sm leading-6 text-muted">
              One member assessed three times: unchanged, with procedure mentions removed from the call
              summaries, and with an explicit denial appended. Confidence should fall in both altered
              variants. Flat confidence is evidence of anchoring rather than reasoning — and needs no
              outcome label to detect.
            </p>
          </div>
          <div className="flex items-end gap-2">
            <label className="text-sm">
              <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted">Member ID</span>
              <input
                value={member} onChange={e => setMember(e.target.value.trim())}
                className="w-32 rounded-lg border border-line px-3 py-2 font-mono"
                aria-label="Member ID to perturb"
              />
            </label>
            <button className="btn-secondary" onClick={runPerturbation} disabled={running !== ''}>
              {running === 'perturb'
                ? <><span className="h-4 w-4 animate-spin rounded-full border-2 border-brand/40 border-t-brand" />Running…</>
                : <><FlaskConical size={16} />Run perturbation</>}
            </button>
          </div>
        </div>

        {perturb && (
          <div className="mt-5">
            <div className="grid gap-3 sm:grid-cols-3">
              {perturb.cases.map(c => (
                <div key={c.case} className="rounded-xl border border-line bg-panel p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted">{c.case}</p>
                  <p className="mt-1 text-3xl font-bold text-brand-dark">{c.confidence.toFixed(2)}</p>
                  <p className="mt-2 text-xs leading-5 text-muted">{c.description}</p>
                </div>
              ))}
            </div>
            <div className={`mt-4 flex items-start gap-3 rounded-xl border p-4 ${
              perturb.verdict.passed ? 'border-brand-soft bg-brand-soft/40' : 'border-amber-200 bg-amber-50'}`}>
              {perturb.verdict.passed
                ? <CheckCircle2 className="mt-0.5 shrink-0 text-brand-dark" size={20} />
                : <AlertTriangle className="mt-0.5 shrink-0 text-amber-700" size={20} />}
              <div>
                <p className="font-semibold">
                  {perturb.verdict.passed ? 'Confidence responds to evidence' : 'Confidence did not move materially'}
                </p>
                <p className="mt-1 text-sm leading-6">{perturb.verdict.interpretation}</p>
                <p className="mt-2 text-sm text-muted">
                  Drop when evidence removed: {perturb.verdict.drop_when_evidence_removed.toFixed(2)} ·
                  drop when contradicted: {perturb.verdict.drop_when_contradicted.toFixed(2)}
                </p>
              </div>
            </div>
          </div>
        )}
      </section>

      <section className="card mt-5">
        <div className="flex items-start gap-3">
          <Target className="mt-0.5 shrink-0 text-brand" size={20} />
          <div>
            <p className="font-semibold">What is not measured here</p>
            <p className="mt-1 max-w-prose text-sm leading-6 text-muted">
              True outcome precision — whether the member actually had the procedure — requires claims
              with roughly a ninety-day lag and is only available after a pilot has run. The checks on
              this page are what makes shadow mode defensible in the meantime: a retrospective score
              against held-out labels, groundedness against the supplied payload, and a direct test of
              whether confidence is reasoning or anchoring.
            </p>
          </div>
        </div>
      </section>
    </>
  )
}
