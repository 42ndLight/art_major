# Self-Review and Definition of Done

The agent must review its own work before reporting completion. A code change is not done merely because it compiles or the page looks correct.

## 1. Before coding

- [ ] Read relevant project docs and current implementation.
- [ ] Checked Git status and preserved unrelated changes.
- [ ] Identified exact roadmap acceptance criteria.
- [ ] Researched external API/framework behaviour where needed.
- [ ] Identified data migration, permissions, payment, communication, and accessibility risks.
- [ ] Planned focused implementation and tests.

## 2. Functional review

- [ ] Every acceptance criterion is mapped to code and a test or explicit manual verification.
- [ ] Forms validate required fields and preserve safe user input on errors.
- [ ] Success and failure states are clear.
- [ ] Empty, loading, pending, and error states exist where appropriate.
- [ ] Project status is separate from payment status.
- [ ] Invoice totals are calculated server-side.
- [ ] Partial payments and outstanding balances are correct.
- [ ] User-facing dates, amounts, and currency labels are unambiguous.
- [ ] No unsupported feature or provider capability is implied.

## 3. Security and privacy review

- [ ] Every artist-owned query is scoped to the current artist.
- [ ] Cross-artist access tests cover customers, projects, invoices, and payments.
- [ ] Public invoice links are high-entropy, revocable as designed, and reveal minimal data.
- [ ] CSRF protection remains enabled for state-changing requests.
- [ ] User content is escaped and no unsafe `mark_safe`/HTML injection has been introduced.
- [ ] Secrets and private tokens are not committed or logged.
- [ ] Payment success depends on verified provider evidence.
- [ ] Provider callback replay/duplicate delivery is handled idempotently.
- [ ] No card number, CVV, mobile-money PIN, or provider secret is stored.
- [ ] SMS tests cannot send real messages accidentally.
- [ ] Customer communication follows configured preferences and consent policy.

## 4. Payment-specific review

- [ ] Amount, currency, provider reference, invoice, and expected state are verified.
- [ ] Repeated callback does not create a second successful payment.
- [ ] Concurrent callbacks cannot over-apply payment or corrupt balances.
- [ ] Failed/pending payments do not reduce the balance.
- [ ] Refund behaviour is explicit and audited if implemented.
- [ ] Browser return URL is not treated as proof of payment.
- [ ] Communication failure does not reverse a confirmed payment.
- [ ] Error messages avoid exposing provider secrets or raw sensitive payloads.

## 5. Frontend and accessibility review

- [ ] Page has one clear primary action and an understandable heading hierarchy.
- [ ] Forms have persistent visible labels, instructions, and field-level errors.
- [ ] All interactions work by keyboard.
- [ ] Focus is visible and not trapped unexpectedly.
- [ ] Status is not communicated by colour alone.
- [ ] Contrast is checked for text, controls, and focus indicators.
- [ ] Layout works at narrow mobile widths and at browser zoom.
- [ ] Controls have adequate hit targets.
- [ ] Motion respects reduced-motion preferences.
- [ ] HTMX updates preserve focus and announce important feedback where appropriate.
- [ ] DaisyUI components have been reviewed for semantics rather than assumed accessible.

## 6. Testing and code quality

- [ ] Correct virtual environment activated.
- [ ] Actual project test/lint commands discovered from configuration.
- [ ] Focused tests run.
- [ ] Relevant broader tests run.
- [ ] Django system checks run where configured.
- [ ] Lint and format checks run where configured.
- [ ] Frontend build/lint checks run if configured.
- [ ] Migration generated and inspected if models changed.
- [ ] No test or linter was weakened merely to obtain a pass.
- [ ] All skipped checks are reported with reasons.

## 7. Diff and documentation review

- [ ] Reviewed `git diff` and `git diff --check`.
- [ ] No unrelated files, secrets, generated artifacts, or debug code included.
- [ ] Documentation matches actual behaviour.
- [ ] Updated `schema.md` and `erd.md` after data model changes.
- [ ] Updated `API.md` after route/contract changes.
- [ ] Updated `research.md` after important external research.
- [ ] Updated roadmap acceptance status only when verified.
- [ ] Known limitations and remaining risks are documented.

## 8. Required final report

Use this structure:

### Summary
What changed and why.

### Acceptance criteria
List each relevant criterion and mark Pass / Partial / Not done with evidence.

### Files changed
List key files.

### Validation performed
Exact commands and observed results. Do not claim checks that were not run.

### Security/accessibility considerations
Important checks and any limitations.

### Outstanding risks
What remains uncertain or incomplete.

### Next step
One small, prioritised follow-up.

## 9. Stop-and-escalate conditions

Do not claim completion if:
- payment verification is bypassed;
- cross-artist access is possible;
- a real SMS/payment is triggered unexpectedly;
- a destructive migration or data-loss action is pending;
- a required external capability has not been verified;
- the product docs materially conflict and the conflict affects behaviour;
- a critical test is failing and no safe resolution has been made.
