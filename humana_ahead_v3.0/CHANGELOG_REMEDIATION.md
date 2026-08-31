# Humana Ahead — remediation changelog

Every item from the critical review, with what changed and where. Grouped by the
priority band from that document.

---

## P0 — Critical

### P0-1 · Evaluation was structurally impossible
**Was:** no outcome label existed anywhere in the eleven CSVs, so precision and
recall could not be computed even in principle.

**Now:** labels are derived from prior-authorization records — a source Agent 1's
system prompt explicitly forbids it from reading, which makes them genuinely held
out. On the current dataset this yields **30 UPCOMING_PROCEDURE, 182 NO_EVIDENCE,
38 AMBIGUOUS** (excluded from scoring).

- `app/services/eval_service.py` — label derivation, scoring, threshold sweep,
  groundedness, self-consistency, perturbation
- `app/api/routes/evaluation.py` — `/api/eval/labels`, `/eval/backtest`,
  `/eval/perturbation`, `/eval/consistency`, `/eval/runs`
- `models.EvalLabel`, `models.EvalRun` — labels live in their own table, read by
  the evaluation module and nothing else
- `pages/EvaluationPage.tsx` — backtest, threshold sweep, groundedness, misses

**Backtesting.** `build_member_context(..., index_date=...)` truncates every
claim and call to what was knowable on a chosen past date, so real precision and
recall are available today rather than after a ninety-day claims lag.

**Stated limitation.** A member can have a real procedure with no authorization
on file, and that population is exactly what this product exists to find. So
NO_EVIDENCE members are treated as negatives and measured precision is a **lower
bound**, not a point estimate. This appears in the API response and on screen.

### P0-2 · Confidence did not discriminate
**Was:** two very different members both scored 0.84, with no calibration behind
the number and a user-movable gate on top of it.

**Now:**
- An explicit five-band rubric in the Agent 1 system prompt, with anchors for
  what each band requires and mandatory downward adjustments for explicit denial,
  continued conservative management, and stale activity
  (`app/agents/care_intent.py`)
- The UI shows a **band**, not a percentage (`components/ConfidenceBand.tsx`).
  Two significant figures imply precision that has not been earned; the raw value
  remains in the detail view
- `/api/eval/perturbation` tests the diagnosis directly: strip the procedure
  mention, then contradict it, and check whether confidence actually moves

### P0-3 · Naive substring provider matching
**Was:** `provider_name.lower() in text` matched "Lee" inside "believe" and
"Park" inside "parking" — and this drove the 30-point network deduction, the
largest in the system.

**Now:** `_mentions()` uses a word-boundary regex with a five-character floor,
and resolution order is reversed so structured sources win: **authorizations →
claims → free text**. Provenance is recorded and shown in the checklist detail
("facility resolved from authorization record"). Covered by seven unit tests.

### P0-4 · Only three procedures worked
**Was:** anything outside knee, hip and cataract fell through to a generic
service group, matched no benefit row, and took a deduction unrelated to the
member.

**Now:** raises `SERVICE_GROUP_UNSUPPORTED`, and the route returns HTTP 422 with
an explanation of why the readiness layer is scoped and that extending it is
configuration rather than code. Fails loudly instead of degrading quietly.

### P0-5 · Non-deterministic output
**Was:** no temperature, so two runs on one member gave different answers.

**Now:** `OPENAI_TEMPERATURE=0.0`, surfaced on `/api/health`. If the model
rejects the parameter the provider degrades once and increments a counter rather
than failing. `/api/eval/consistency` measures the spread across repeated runs.

### P0-6 · Circular validation
Not a code change — a presentation answer. Worth knowing: **only 37% of the
synthetic Agent Assist summaries contain an explicit procedure word**, and
several positives are deliberately oblique. The dataset is harder than it looks,
but the POC still validates the reasoning layer rather than proving the signal
exists in production summaries. Week one of a pilot has to measure that.

---

## P1 — Significant

| ID | Fix | Where |
|---|---|---|
| P1-1 | Strict JSON schema mode, one repair retry, counters for repairs and retries | `openai_provider.py` |
| P1-2 | Results persisted to `care_intent_results` / `readiness_results`; module-global dicts removed | `result_store.py`, `models.py` |
| P1-3 | Concurrent scan via `asyncio.gather` with a semaphore; each coroutine gets its own session | `routes/agents.py` |
| P1-4 | Confidence removed from the readiness cache key — it never affected the output | `readiness.py` |
| P1-5 | `activity_filter.AS_OF` now reads `settings.data_as_of` | `activity_filter.py` |
| P1-6 | `SCORE_WEIGHTS` named and documented, `WEIGHT_RATIONALE` returned to the UI | `readiness.py` |
| P1-7 | Presentation answer. Existing controls: `store:false`, ID-only main packet, transcript fetched only on explicit allow-listed request | — |
| P1-8 | `ErrorBoundary` at app root and around the routed outlet | `components/ErrorBoundary.tsx` |
| P1-9 | **Safety defect.** Removed `memberId='M0001'` default — a missing route param silently drafted outreach for another member. Now fails closed | `OutreachPage.tsx` |
| P1-10 | Clinical predictions no longer written to `sessionStorage`; only sidebar state and selected IDs persist | `AppContext.tsx` |

---

## P2 — Product judgment

| ID | Fix |
|---|---|
| P2-1 | `advocate_contact.risk_level` retained and documented as a separate administrative signal; ranking use noted rather than left silently unused |
| P2-2 | Settings framed as operator controls with the rubric explained; threshold no longer the only governance lever |
| P2-3 | `/api/outreach/decisions/stats` — approve/edit/reject rates by message class and top issue. `was_edited` and `original_message` now captured. This is the learning loop |
| P2-4 | Agent 2's remit stated honestly: it prioritises and writes one sentence, and its choice is validated against the checklist and discarded on disagreement |
| P2-5 | `message_class` on every draft (INFORMATIONAL, BENEFIT_SURFACING, COST_DISCLOSURE, CARE_REDIRECTION, CLINICAL_ADJACENT) with a per-class gating policy. Governance moves from confidence to consequence |
| P2-6 | `/api/members` paginated with `offset`, `limit`, `has_more`, plus a `candidates_only` view backed by the Tier-0 filter (132 of 250) |
| P2-7 | `role="alert"` / `role="status"` on banners, `aria-busy` on the scan button, `aria-live` on progress, labelled inputs, non-colour status cues |
| P2-8 | Concurrency plus per-member progress; the scan no longer blocks on a single spinner |
| P2-9 | Single `POST /members/{id}/outreach/decision`. Saving for review previously posted to `/reject`, so endpoint metrics counted saves as rejections. Old routes retained as aliases |
| P2-10 | Notices separated from errors — informational messages no longer render in the error banner |

---

## P3 — Production readiness

| ID | Fix |
|---|---|
| P3-1 | Not implemented — auth would break the login-free demo. Documented as a release requirement: attributable approvals need an authenticated advocate identity |
| P3-2 | Exponential backoff with jitter on 429 and 5xx, `OPENAI_MAX_RETRIES`, retry counter |
| P3-3 | Token estimator now counts word and punctuation pieces with a long-word correction instead of `len/4`; rows using an estimate are counted separately from API-reported ones |
| P3-4 | `correlation_id` and `prompt_version` recorded on every result and usage row |
| P3-5 | **32 unit tests** covering word-boundary matching, score weights, canonicalisation, banding, groundedness, perturbation and scoring |
| P3-6 | Landing token tile returns `has_usage` so a fresh database does not display a bare zero |

---

## New API surface

```
GET  /api/eval/labels                    held-out labels, method and limitation
POST /api/eval/labels/rebuild            re-derive at a given index date
POST /api/eval/backtest                  precision, recall, F1, threshold sweep
POST /api/eval/perturbation              does confidence respond to evidence
POST /api/eval/consistency               spread across repeated runs
GET  /api/eval/runs                      run history
GET  /api/outreach/decisions/stats       approve / edit / reject by class
POST /api/members/{id}/outreach/decision unified decision endpoint
GET  /api/members?offset=&limit=&candidates_only=
```

---

## Verification

```
32 passed in 1.79s          backend/tests/
15/15 endpoints OK          smoke test across every route
tsc --noEmit                clean
vite build                  clean
labels derived              30 / 182 / 38
pagination                  250 total, 132 candidates
edit tracking               was_edited True, class recorded
```

## Post-review corrections

Two defects introduced by the remediation itself, found on first run and fixed:

**Readiness batch response shape.** Rewriting `agents.py` for concurrency also
changed `/assessments/readiness` from `{member, care_intent, readiness}` to
`{member_id, assessment}`, which the Readiness Results page could not read -
`Cannot read properties of undefined (reading 'member_id')`. Restored the
original contract and added `processed_count` plus a `skipped` list so members
that cannot be assessed are explained rather than silently dropped. The page now
filters malformed rows defensively and renders skip reasons.

**Tokens tile.** Removed from the landing page entirely rather than relabelled.
`prompt_tokens_used` remains on the API for the Impact page, which is where
session spend belongs.

**Session restore.** Because clinical predictions are no longer written to
`sessionStorage`, the Readiness Results page now reloads saved assessments from
the server on mount. This makes the error boundary's claim that results are
stored server-side actually true.

**Outreach was hard to reach.** The Approve and Send action existed only inside
the expanded readiness card, which made it feel removed. Added a dedicated
**Outreach** screen in the navigation, positioned before Evaluation, listing
every member with a completed readiness assessment alongside the drafted
message, its message class, and Approve & Send / Save for Review / Do Not
Contact. Also promoted a "Review outreach" button onto the collapsed readiness
card.

**Contact likelihood was never displayed.** The backend has always returned
`advocate_contact.confidence`, but the scan results screen only rendered the
risk badge. It now shows the percentage next to the badge, labelled as the
chance of the member contacting an advocate soon - a separate administrative
signal from care-intent confidence.

**The notification now carries the whole checklist.** Outreach previously sent a
single generic sentence, so a member told that "an item needs attention" still
had to call to find out which one - the exact behaviour this product exists to
prevent. `build_outreach_draft` now returns the full readiness checklist in
member-facing language, a headline, the ready-item count, the readiness score,
and the highlighted next action. `NotificationPreview` renders what the member
would actually receive: the highlighted issue in its own callout, then every
checklist line with a status label as well as a colour.

**Landing grid.** Removing the tokens tile left `sm:grid-cols-5` with four
tiles, hence the empty cell. Now `sm:grid-cols-4`.

**The notification now resolves rather than refers.** Outreach previously ended
with "a Member Advocate can review this with you" - which is a better way of
generating the call this product exists to prevent. `_resolution()` now picks
one of four modes from the deterministic checklist:

| Mode | When | What the member sees |
|---|---|---|
| `CHOOSE_OPTION` | A network issue with in-network alternatives available | The alternatives as selectable options, and a confirm action |
| `CONFIRM` | An unused benefit the plan can arrange | A yes/no |
| `NO_ACTION` | The plan is settling it with the provider | An explicit statement that nothing is needed from them |
| `ADVOCATE` | Nothing above applies | A callback-time choice, with the reason recorded |

An advocate is mentioned only in `ADVOCATE` mode, and `advocate_reason` records
why no self-service path existed. The notification carries the full checklist
plus the in-network alternatives, and the member picks a facility inside the
message.

Verified on the two demo members: Robert Carter's out-of-network facility
produces `CHOOSE_OPTION` with three selectable in-network facilities and no
mention of an advocate; Margaret Lewis's conditional referral produces
`NO_ACTION` - "we're following up on it directly, there's nothing you need to
do."

---

## Not fixed, by choice

- **P0-6, P1-7, P3-1** are presentation answers or would break the demo. The
  three-procedure scope limit (P0-4) now fails loudly, but should still be stated
  on a slide rather than discovered.
- Chunk-size warning on the frontend build is cosmetic; code splitting was not
  worth the churn before a presentation.
