type Band = 'HIGH' | 'MODERATE_HIGH' | 'MODERATE' | 'LOW' | 'MINIMAL'

const LABEL: Record<Band, string> = {
  HIGH: 'High', MODERATE_HIGH: 'Moderate-high', MODERATE: 'Moderate',
  LOW: 'Low', MINIMAL: 'Minimal',
}
const TONE: Record<Band, string> = {
  HIGH: 'bg-brand-soft text-brand-dark',
  MODERATE_HIGH: 'bg-brand-soft text-brand-dark',
  MODERATE: 'bg-amber-50 text-amber-800',
  LOW: 'bg-slate-100 text-slate-700',
  MINIMAL: 'bg-slate-100 text-slate-500',
}

/**
 * Confidence is displayed as a band rather than a percentage.
 *
 * The score is an evidence score, not a calibrated clinical probability. Two
 * significant figures imply a precision that has not been earned while the
 * score is uncalibrated, so the band carries the decision and the raw value
 * stays available in the detail view for anyone who wants it.
 */
export default function ConfidenceBand({ band, confidence, reason, showRaw = false }:
  { band?: string; confidence: number; reason?: string; showRaw?: boolean }) {
  const key = (band as Band) || 'MINIMAL'
  return (
    <div>
      <span className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ${TONE[key] || TONE.MINIMAL}`}>
        {LABEL[key] || 'Minimal'} evidence
      </span>
      {showRaw && (
        <p className="mt-1 text-xs text-muted">
          Evidence score {confidence.toFixed(2)} · not a calibrated clinical probability
        </p>
      )}
      {reason && <p className="mt-1 max-w-prose text-xs leading-5 text-muted">{reason}</p>}
    </div>
  )
}
