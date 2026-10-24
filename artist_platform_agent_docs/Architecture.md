# Architecture and User Workflows

## 1. Purpose

Describe the intended system boundaries without treating unverified choices as implemented. **Proposed stack:** Django, PostgreSQL, HTMX, Alpine.js, Tailwind CSS, and daisyUI. The repository currently has no application code; confirm this stack during roadmap Stage 0 before scaffolding.

## 2. Stack

- **Django:** application framework, routing, authentication, forms, validation, permissions, business logic, template rendering, and integrations.
- **PostgreSQL:** relational source of truth for users, customers, projects, invoices, line items, payment attempts/events, and communications.
- **Django templates:** render the HTML experience.
- **HTMX:** progressively enhance server-rendered pages for partial updates, inline forms, search/filter, and modal content where appropriate.
- **Alpine.js:** small client-side interactions such as toggles, dropdowns, and simple form affordances. It is not a replacement for server-side validation.
- **Tailwind CSS:** utility-based styling and design tokens.
- **daisyUI:** accessible-minded component starting points and consistent component classes; generated markup still requires accessibility review.
- **Africa's Talking:** possible communications integration. Confirm the actual event criteria, required channel, account availability, and official API details first.
- **Payment provider:** initially one researched provider, using hosted checkout/payment links where feasible. Selection is pending verified requirements and availability.

Do not add a separate SPA, DRF, Celery, Redis, or extra infrastructure without a demonstrated requirement. If scheduled messages or asynchronous delivery are necessary, first assess the simplest reliable approach and document trade-offs.

## 3. High-level request flow

1. Browser requests a page.
2. Django authenticates the artist when required and checks ownership/permissions.
3. Django validates form input and performs business logic.
4. PostgreSQL stores the canonical application state.
5. Django renders a full page or an HTMX partial.
6. Alpine.js enhances small interactions but never decides permissions or financial truth.
7. External provider callbacks are validated and processed idempotently by Django.
8. Communications are sent through a dedicated service boundary; communication failures must not undo successful payment state.

## 4. Application boundaries

Suggested Django app boundaries (names are proposals, inspect existing code before adopting):
- `accounts`: artist authentication, artist profile, preferences.
- `customers`: customer records and notes.
- `projects`: commissions and project status.
- `billing`: invoices, line items, payment attempts, payment events, receipts.
- `communications`: message preferences, outbound message records, Africa's Talking adapter.
- `core`: dashboard, shared utilities, health checks, common layout.

Keep app count small if the repository is new. Do not create an app for every model. Avoid circular imports; put shared domain operations in a clear service layer when useful.

## 5. User roles and workflows

### Artist — first-run onboarding
1. Registers and verifies account as supported by the chosen auth flow.
2. Completes display name/business name and default currency.
3. Sees a concise onboarding checklist: add customer, create project, create invoice, configure payment provider, test communication settings.
4. Can skip nonessential profile details and return later.

Acceptance: an artist cannot access another artist's records, and onboarding does not falsely imply that payments are ready before provider setup is complete.

### Artist — customer management
1. Opens Customers.
2. Adds customer name and at least one suitable contact method; optional email, phone, country, and notes.
3. Searches and filters their own customers.
4. Opens a customer detail view showing related projects and invoices.
5. Edits or archives a customer without destroying financial history.

### Artist — project/commission management
1. Creates a project linked to a customer.
2. Records title, brief, agreed amount/currency, due date, and status.
3. Updates status as work progresses.
4. Views associated invoices and payment progress.
5. Marks work complete separately from whether the invoice is paid.

Proposed statuses: `inquiry`, `accepted`, `in_progress`, `completed`, `on_hold`, `cancelled`. Validate the final list against the UX.

### Artist — invoice and payment request
1. Selects a customer and optionally a project.
2. Adds invoice line items, quantity, unit price, due date, and currency.
3. Server calculates line totals and invoice total.
4. Saves an invoice with a unique human-readable reference.
5. Creates a secure private customer link.
6. Shares the link through copy/share controls or a communication channel.
7. Can request a deposit or instalment up to the outstanding amount, where supported.

After issue, avoid silently changing historical totals. Use a documented draft/edit/issued/void lifecycle and preserve auditability.

### Customer — private invoice and payment
1. Opens a high-entropy private link without creating an account.
2. Sees artist/business name, invoice reference, item description, amount, currency, due date, amount paid, and balance due, with unnecessary personal data omitted.
3. Chooses an available payment method and proceeds to the provider's hosted checkout or supported flow.
4. Sees a neutral pending/processing state while payment is unconfirmed.
5. Sees confirmation only after verified provider confirmation.
6. Can access a receipt or confirmation page without being given access to the artist dashboard.

### Payment callback/reconciliation
1. Provider sends a callback/webhook or the app performs a documented server-side verification request.
2. Django validates authenticity and expected transaction details according to official provider documentation.
3. Processing is idempotent and safe under retries/concurrency.
4. A payment record/event is updated once.
5. Invoice balance/status is recalculated from valid payment records.
6. Receipt and transactional notification are queued/sent safely.
7. Failed communication does not roll back the financial event.

### Africa's Talking communication workflow (MVP requirement)
1. Artist explicitly enables transactional SMS and provides/validates a customer phone number where needed.
2. The app triggers an allowed message after events such as invoice issued, payment confirmed, or project update, based on consent and user preferences.
3. A communication record stores recipient, purpose/template key, provider message ID if returned, status, timestamps, and redacted failure reason.
4. Sandbox mode is used during development. Tests mock the provider and never send real SMS.
5. If the SMS fails, the invoice/payment workflow remains valid and the artist can see the failure or retry safely.

Do not add marketing campaigns to the MVP.

### Artist — dashboard
- Show summary values only from persisted, correctly scoped records.
- Distinguish gross invoice totals, confirmed payments, and outstanding balances.
- Use explicit date ranges and currency labels.
- Do not aggregate different currencies into a misleading single amount.
- Provide links from metrics to the relevant filtered records.

### Free and Pro plans
The initial MVP should not block core business records behind a paywall. Advanced analytics, branding, automation, and exports may later be plan-gated. Avoid implementing complex subscription billing until demand and pricing are validated.

## 6. Security and trust boundaries

- Authenticated artist area: login required and every query scoped to the artist.
- Public customer invoice view: only a valid private token grants access to a minimal invoice projection.
- Payment provider: never trust client redirects as evidence of payment.
- Africa's Talking: treat API response and delivery status as external, fallible data.
- Secrets: environment variables/secrets manager only.
- Logs: redact secrets, payment tokens, phone numbers, and private links.
- Use HTTPS in deployed environments, CSRF protection, secure cookies, and Django's production deployment checklist.

## 7. Deployment and operations

Deployment provider is undecided. Before release, document:
- supported Python and PostgreSQL versions;
- environment variables and secret handling;
- migration procedure and backup/restore;
- static asset build procedure;
- health checks and error logging;
- provider sandbox/production separation;
- HTTPS, allowed hosts, secure cookies, and `DEBUG=False`;
- how to disable external SMS/payment calls quickly.

## 8. Decisions still open

- Exact Africa's Talking hackathon communication requirements.
- Exact Africa's Talking product/API and supported regions.
- Initial payment provider and supported artist countries/currencies.
- Whether customers receive email, SMS, or both for each event.
- Final project and invoice state transitions.
- Hosting and deployment platform.
- Whether asynchronous jobs are needed for reliable notifications.
