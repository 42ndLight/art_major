# Mandatory Project Rules

These rules apply to every agent, contributor, and code change. If a task conflicts with a rule, stop and explain the conflict instead of silently bypassing it.

## 1. Repository and environment safety

1. Inspect the repository and `git status` before editing.
2. Never delete, reset, overwrite, or revert user work without explicit approval.
3. Use the project's existing virtual environment if present. Do not create a new environment or install packages until you inspect project setup.
4. Activate the virtual environment before running Python, Django, migrations, tests, formatting, or linting. Examples:
   - Linux/macOS: `source .venv/bin/activate` (or the actual environment path found in the repository)
   - Windows PowerShell: `.venv\Scripts\Activate.ps1`
5. Verify the interpreter and Django environment when uncertain: `which python`, `python --version`, `python -m django --version`.
6. Do not assume the virtual environment is named `.venv`; inspect first.
7. Never run commands against production or a database containing valuable data unless explicitly authorised.
8. Never run `flush`, destructive migration resets, `rm -rf`, `git reset --hard`, `git clean -fd`, or force-push as a routine fix.
9. Do not start a development server unless it is needed to verify a specific browser flow. If started, use the project's documented command, avoid port conflicts, and stop the process when finished.
10. Never claim a server is running, a test passed, or a feature works unless verified.

## 2. Django conventions

- Use Django's supported patterns and keep views thin.
- Prefer Django forms and ModelForms for server-rendered form validation.
- Use named URL patterns and `reverse()`/`{% url %}` instead of hard-coded internal paths.
- Enforce ownership and permissions on the server, not just in templates or JavaScript.
- Use transactions for multi-record financial operations where needed.
- Use database constraints for invariants that must hold even under concurrent requests.
- Use timezone-aware datetimes and Django's timezone utilities.
- Avoid N+1 queries; use `select_related()` and `prefetch_related()` where appropriate.
- Never expose Django debug pages in production.
- Do not add DRF or a separate JSON API layer unless the current task or product requirement needs it. HTMX requests can use normal Django views.

## 3. Payments and financial correctness

- Treat money as decimal values, never binary floating-point.
- Store currency explicitly for each invoice/payment; do not silently convert.
- Define invoice totals from validated line items and enforce server-side calculation.
- Never trust client-submitted totals, payment status, owner IDs, provider references, or currency conversions.
- Verify payment callbacks/webhooks according to the provider's current official specification.
- Make callbacks idempotent: replaying the same event must not create duplicate successful payments or receipts.
- Validate amount, currency, invoice reference, provider reference, and expected payment state before applying a payment.
- Separate `pending`, `succeeded`, `failed`, `cancelled`, and `refunded` states where relevant; do not collapse all outcomes into a boolean.
- Record an auditable payment event/history. Do not silently overwrite historical financial facts.
- Never mark a payment successful from a browser redirect alone.
- Do not store payment card data, CVV, PIN, or secret credentials.
- Real payment, refund, or payout actions require explicit approval during development.

## 4. Private links and authorisation

- All artist-owned records must be scoped to the authenticated artist on every server request.
- Never rely on an object ID alone for access control.
- Use cryptographically secure, unguessable tokens for private customer invoice/payment links; do not use sequential IDs as secrets.
- Store token digests instead of raw tokens when practical; never log full tokens.
- Provide revocation/expiry behaviour where appropriate.
- Expose only the minimum invoice data needed by the customer.
- Protect state-changing requests with Django CSRF protection.
- Do not use `mark_safe` or disable autoescaping for untrusted user content without a reviewed, justified sanitisation strategy.
- Escape user-provided names, descriptions, notes, and project text in templates.

## 5. Africa's Talking communication rules

- Confirm the hackathon's actual communication requirements and the currently supported Africa's Talking product/API before coding.
- Keep credentials in environment variables or a secrets manager; never commit them.
- Use sandbox/test credentials and test destinations during development.
- Never send real SMS to a customer as part of automated tests.
- Require a clear consent/opt-in basis for non-essential messages and provide an opt-out path where applicable.
- Distinguish transactional messages (invoice/payment/project updates) from marketing.
- Avoid including sensitive invoice details, private tokens, or full payment information in SMS.
- Record delivery/provider message IDs and statuses where available; do not treat API acceptance as proof that a message reached the handset.
- Implement safe failure handling: a failed SMS must not roll back a successful payment.
- Rate-limit message-triggering endpoints and prevent duplicate notifications.
- Do not retry indefinitely; use bounded retries and log redacted error details.

## 6. Tests, linting, and formatting

Before testing, activate the correct virtual environment and inspect `pyproject.toml`, `pytest.ini`, `tox.ini`, `Makefile`, CI configuration, and/or `requirements*.txt` to discover the project's actual tools.

Run the narrowest relevant test first, then broader checks. Typical commands, only if configured:
- `python manage.py check`
- `python manage.py test`
- `pytest`
- `ruff check .`
- `ruff format --check .`
- `black --check .`
- `isort --check-only .`
- template/lint checks configured by the repository
- `npm run lint` / `npm run build` only if a frontend package and scripts exist

Do not install a linter just to run an assumed command. If a check is unavailable, report it as not run and explain why. Fix introduced failures; do not hide them by weakening tests or lint rules without approval.

## 7. Migrations and schema changes

- Create migrations with Django's migration tooling; do not hand-edit generated migration files unless necessary and reviewed.
- Inspect migration output and migration plan before applying it to any valuable database.
- Test forward migration on a disposable/local test database.
- Avoid destructive or irreversible schema changes without explicit approval.
- Update `schema.md` and `erd.md` when entity fields, constraints, or relationships change.
- Never edit an already-applied migration to change production history; create a new migration.

## 8. Accessibility and frontend

- Use semantic HTML, visible labels, keyboard access, and clear focus indicators.
- Do not use colour alone to communicate status.
- Respect reduced-motion preferences.
- Keep forms usable on narrow screens and with zoom.
- Use HTMX for server-driven interactions and Alpine.js only for lightweight client-side state.
- Do not introduce a large client-side framework without approval.
- Follow `styling_guide.md`; avoid arbitrary one-off styling when a design token or daisyUI component exists.

## 9. Code quality and scope

- Keep changes focused on the acceptance criteria.
- Prefer readable, boring code over clever abstractions.
- Avoid speculative abstractions and premature generalisation.
- Add regression tests for bug fixes.
- Do not duplicate business rules across templates and views when they can be enforced once on the server.
- Update docs when behaviour or contracts change.
- Review `git diff` before declaring completion.


> Compatibility note: `rules.md` is the canonical filename. This file is provided because some agent configurations look for `rule.md`. Keep both synchronised until all tooling points to `rules.md`.
