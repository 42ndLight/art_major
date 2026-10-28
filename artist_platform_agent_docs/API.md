# Application Routes and Integration Contracts

**Proposed contract only:** the planning documents suggest Django server-rendered views, HTML forms, and HTMX partial responses. This repository does not yet contain an application, so these routes are not implemented. Confirm the stack and provider choices before building the contracts below.

## 1. Conventions

- Prefer normal Django views/forms over a separate REST API unless a real client integration requires JSON.
- Use named URL patterns.
- For HTMX requests, return an HTML fragment with a clear success/error state; for normal requests, return a full page or redirect using Post/Redirect/Get.
- Validate all inputs server-side.
- Apply artist ownership filters to every private record query.
- Use CSRF protection for state-changing requests.
- Use a consistent status code and safe error response.
- Do not expose stack traces, secrets, internal IDs unnecessarily, or payment-provider payloads.
- Public invoice URLs use an unguessable token, not an invoice database ID as the secret.

## 2. Artist routes (proposed)

| Method   | Route                               | Purpose                                  | Access              |
| -------- | ----------------------------------- | ---------------------------------------- | ------------------- |
| GET/POST | `/accounts/signup/`                 | Register artist                          | Public              |
| GET/POST | `/accounts/login/`                  | Sign in                                  | Public              |
| POST     | `/accounts/logout/`                 | Sign out                                 | Authenticated       |
| GET/POST | `/settings/profile/`                | Edit artist profile and preferences      | Artist              |
| GET      | `/dashboard/`                       | Summary of projects and financial status | Artist              |
| GET      | `/customers/`                       | List/search own customers                | Artist              |
| GET/POST | `/customers/new/`                   | Create customer                          | Artist              |
| GET/POST | `/customers/<uuid:pk>/edit/`        | Edit own customer                        | Artist              |
| GET      | `/customers/<uuid:pk>/`             | Customer details/history                 | Artist              |
| POST     | `/customers/<uuid:pk>/archive/`     | Archive customer                         | Artist              |
| GET      | `/projects/`                        | List/filter own projects                 | Artist              |
| GET/POST | `/projects/new/`                    | Create project                           | Artist              |
| GET      | `/projects/<uuid:pk>/`              | Project detail                           | Artist              |
| GET/POST | `/projects/<uuid:pk>/edit/`         | Edit project                             | Artist              |
| POST     | `/projects/<uuid:pk>/status/`       | Change allowed project status            | Artist              |
| GET      | `/invoices/`                        | List/filter invoices                     | Artist              |
| GET/POST | `/invoices/new/`                    | Create draft invoice                     | Artist              |
| GET      | `/invoices/<uuid:pk>/`              | Invoice detail                           | Artist              |
| POST     | `/invoices/<uuid:pk>/issue/`        | Issue invoice and create private link    | Artist              |
| POST     | `/invoices/<uuid:pk>/void/`         | Void eligible invoice                    | Artist              |
| POST     | `/invoices/<uuid:pk>/payment-link/` | Create/recreate provider payment request | Artist              |
| GET      | `/payments/`                        | Payment history and statuses             | Artist              |
| GET      | `/communications/`                  | Message history/status                   | Artist              |
| POST     | `/communications/preferences/`      | Update permitted communication settings  | Artist              |
| POST     | `/communications/test/`             | Sandbox-only test SMS where configured   | Artist/admin policy |

Use POST (not GET) for state changes. Confirm destructive/irreversible transitions and enforce valid state transitions.

## 3. Public customer routes (proposed)

| Method | Route | Purpose |
|---|---|---|
| GET | `/i/<token>/` | Display minimal invoice details via private token |
| GET/POST | `/i/<token>/pay/` | Create a payment attempt / redirect to supported checkout |
| GET | `/payment/return/` | Display neutral processing/result page; not proof of payment |
| GET | `/receipt/<token>/` | Display a limited receipt using a separate secure token or appropriately protected reference |

Requirements:

- Token must be generated with a cryptographically secure random generator.
- Prefer storing a digest of the token and comparing securely.
- Public responses must not reveal whether arbitrary invoice IDs exist.
- Apply throttling/rate limits where feasible.
- Do not expose customer notes, internal project notes, private payment metadata, or artist-wide statistics.
- Payment return page must say “processing” until server-side verification confirms success.

## 4. Payment provider adapter contract

The exact provider is pending research. Keep provider-specific code behind a small adapter/service boundary with operations such as:

- `create_checkout(invoice, amount, currency, idempotency_key)`
- `verify_callback(request)`
- `verify_transaction(provider_reference)`
- `normalise_provider_status(payload)`
- `parse_provider_reference(payload)`

These are conceptual operation names, not mandatory Python method names.

For every payment event:

1. Verify signature/authentication according to current official provider documentation.
2. Match provider reference, invoice, amount, currency, and expected state.
3. Deduplicate repeated callbacks/events.
4. Update payment and invoice balances in a database transaction.
5. Record a safe audit event.
6. Trigger receipt/communication after the financial state is committed.
7. Handle retries without duplicate charges, payments, or messages.

Do not invent provider callback signatures, endpoints, or authentication rules. Research and cite the exact official documentation in `research.md`.

## 5. Africa's Talking communications contract

The hackathon requires a communications feature, but the exact event brief and channel must be verified. The provisional design is transactional SMS via Africa's Talking, if supported and appropriate.

Potential internal operation:

- `send_transactional_sms(recipient, template_key, context, idempotency_key)`

Requirements:

- API key, username, sender ID, and environment must come from environment configuration, following the official API's actual requirements.
- Sandbox and production settings must be separate.
- Allowlisted test recipients or mocked calls must be used in automated tests.
- Record request purpose, provider response/message ID, status, and redacted error.
- Do not include full invoice details, payment tokens, or sensitive customer data in SMS.
- Respect user preferences, consent, and applicable messaging rules.
- Message send failure must not roll back payment confirmation.
- Avoid duplicate SMS on repeated provider callbacks.

Potential MVP events:

- Invoice issued: “You have a new invoice from [artist/business]. View details: [private link]”
- Payment confirmed: “Your payment has been confirmed. Receipt: [secure receipt link]”
- Project update: only when artist explicitly initiates the update.

Do not send messages automatically to real recipients until the user explicitly authorises live messaging and production credentials are configured.

## 6. Form validation and error behaviour

- Invalid user input: show field-level errors and preserve safe submitted values.
- Permission failure: return 403 or a non-disclosing 404 according to the resource's privacy policy.
- Expired/revoked private link: show a clear, non-sensitive message and a safe way to contact the artist.
- Provider unavailable: explain that payment initiation failed and allow safe retry without duplicate charge.
- Pending payment: show a pending state and do not issue a success receipt.
- SMS provider failure: record failure and let the main workflow continue.
- Currency mismatch: reject rather than silently convert.
- Overpayment attempt: reject or apply a documented policy; do not silently accept an unexpected amount.

## 7. API documentation maintenance

Update this file whenever routes, forms, external integrations, public-link behaviour, permissions, or response contracts change. Add integration tests for payment callbacks and private-link access.
