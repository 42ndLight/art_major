# Database Schema Specification

This is a proposed logical schema. Confirm against the repository and `erd.md` before implementation. Use Django models and migrations as the implementation source of truth.

## Conventions

- Use UUID primary keys for externally addressable records where practical; do not expose sequential IDs as security tokens.
- Use `created_at` and `updated_at` timestamps where relevant.
- Use `DecimalField` for money and store ISO-style currency codes explicitly.
- Use `settings.AUTH_USER_MODEL` for the artist account relationship.
- Artist-owned records must have a clear owner path and enforced server-side scoping.
- Add database constraints and indexes for important invariants and common lookups.
- Keep financial history auditable; do not erase successful payments to make balances appear correct.

## Entities

### 1. Artist / User
Use Django's configured user model. If a custom user model is required, define it before the first migration. Do not retrofit a custom user model casually after production data exists.

Suggested fields:
- `id`: UUID or configured user primary key
- `email`: unique login identifier if email-based authentication is selected
- `password`: Django-managed password hash only
- `is_active`, `is_staff`, `date_joined`
- `display_name`
- `business_name` (optional)
- `default_currency` (ISO-style code, initial default configurable)
- `timezone` (optional)
- `created_at`, `updated_at`

For inbound SMS command ownership, `ArtistProfile` also stores `phone_number`, `phone_verified_at`, a hashed one-time verification code, expiry, and a failed-attempt count. Verified phone numbers are unique across artist accounts. The OTP is short-lived and invalidated after five failed attempts.

Authentication approach and whether profile fields live on a separate `ArtistProfile` are open decisions. Prefer a separate profile if it keeps auth concerns clean.

### 2. Customer
Fields:
- `id`: UUID
- `artist_id`: FK to owner/artist
- `name`: required
- `email`: optional
- `phone_number`: optional, normalised where feasible
- `country_code` or country (optional)
- `notes`: optional, length-limited
- `archived_at`: nullable timestamp for soft archive
- `created_at`, `updated_at`

Constraints/indexes:
- Index `(artist_id, name)` and relevant search/contact fields.
- Do not assume email is globally unique.
- A customer should have at least one usable contact detail if that is chosen as a business rule; validate consistently.
- Archived customers remain associated with historical invoices and payments.

### 3. Project
Fields:
- `id`: UUID
- `artist_id`: FK to owner/artist
- `customer_id`: FK to Customer
- `title`: required
- `description` or `brief`: optional
- `agreed_amount`: Decimal, optional until agreed
- `currency`: ISO-style code, required when amount is set
- `due_date`: nullable date
- `status`: inquiry / accepted / in_progress / completed / on_hold / cancelled (final choices to validate)
- `completed_at`: nullable timestamp
- `created_at`, `updated_at`

Rules:
- The customer must belong to the same artist.
- Work status and payment status are separate concepts.
- Preserve project history when an invoice or payment exists.

### 4. Invoice
Fields:
- `id`: UUID
- `artist_id`: FK to owner/artist
- `customer_id`: FK to Customer
- `project_id`: nullable FK to Project
- `invoice_number`: unique per artist, human-readable
- `status`: draft / issued / partially_paid / paid / overdue / void (derive where appropriate; avoid contradictory manually maintained state)
- `currency`: required
- `issue_date`: date
- `due_date`: nullable date
- `subtotal`: Decimal, calculated server-side
- `discount_amount`: Decimal default zero if supported
- `total_amount`: Decimal, calculated server-side
- `public_token_digest`: secure token digest for private link, nullable for drafts
- `issued_at`, `voided_at`: nullable timestamps
- `created_at`, `updated_at`

Rules:
- Invoice and customer must belong to the same artist.
- If project is set, project must belong to the same artist and ordinarily the same customer.
- Never trust submitted totals.
- Decide whether `partially_paid`, `paid`, and `overdue` are computed from payments and dates or materialised with consistent update logic. Do not permit inconsistent states.
- `void` invoices cannot receive new payment attempts.
- A private link must be revocable and unguessable.

### 5. InvoiceLine
Fields:
- `id`: UUID
- `invoice_id`: FK to Invoice
- `description`: required
- `quantity`: Decimal with positive constraint
- `unit_price`: Decimal, non-negative unless an explicit credit-line policy is adopted
- `line_total`: calculated server-side or calculated on read; do not trust browser value
- `position`: integer for display order

Rules:
- Define rounding/decimal precision consistently.
- Once issued, changes should follow a documented correction/void process rather than silently rewriting historical amounts.

### 6. Payment
Represents an actual provider transaction or a manually recorded payment (manual recording, if allowed, must be labelled clearly).

Fields:
- `id`: UUID
- `artist_id`: FK to owner/artist
- `invoice_id`: FK to Invoice
- `provider`: provider key, e.g. configured provider slug
- `provider_reference`: nullable until known; unique within provider where available
- `idempotency_key` or provider event key: unique where applicable
- `amount`: Decimal, positive
- `currency`: required
- `status`: pending / succeeded / failed / cancelled / refunded / partially_refunded as supported
- `payment_method`: provider-defined safe label, optional
- `initiated_at`, `confirmed_at`, `updated_at`
- `failure_code`: safe, non-sensitive code
- `failure_message`: redacted and length-limited

Rules:
- Payment currency must match invoice currency unless a verified explicit conversion flow is designed.
- A payment cannot exceed the outstanding amount unless overpayment handling is explicitly supported.
- Only verified successful payments reduce the outstanding balance.
- Provider callback processing must be idempotent and transaction-safe.
- Never store card numbers, CVV, PIN, or provider secrets.

### 7. PaymentEvent / ProviderEvent
Optional but recommended for auditable integration processing.

Fields:
- `id`: UUID
- `provider`: provider key
- `external_event_id`: provider event ID where available
- `payment_id`: nullable FK to Payment
- `event_type`: short string
- `payload_digest` or redacted minimal metadata; do not store secrets or unnecessary sensitive payloads
- `processing_status`: received / processed / ignored / failed
- `received_at`, `processed_at`
- `error_code`: redacted

Constraint:
- Unique `(provider, external_event_id)` where provider guarantees a stable event ID.

### 8. CommunicationPreference
Fields:
- `id`: UUID
- `artist_id`: FK to artist
- `customer_id`: FK to customer
- `channel`: sms / email
- `transactional_enabled`: boolean
- `consent_status`: unknown / opted_in / opted_out / not_required_only (validate applicable legal/provider rules)
- `consent_recorded_at`: nullable timestamp
- `updated_at`

Rules:
- A customer belongs to the same artist.
- Store only communication preferences and evidence needed for the product; document consent policy.
- Transactional and marketing communication are separate; marketing is out of scope.

### 9. CommunicationMessage
Fields:
- `id`: UUID
- `artist_id`: FK to artist
- `customer_id`: nullable FK to customer
- `invoice_id`: nullable FK to invoice
- `channel`: sms / email
- `purpose`: invoice_issued / payment_confirmed / project_update / reminder
- `recipient_redacted` or protected recipient reference; limit sensitive exposure
- `template_key`: identifier, not arbitrary executable template content
- `provider_message_id`: nullable
- `status`: queued / submitted / delivered / failed / unknown (map to provider capabilities)
- `attempt_count`: integer
- `last_error_code`: redacted
- `created_at`, `submitted_at`, `delivered_at`, `updated_at`

Rules:
- Do not claim delivered unless provider delivery data confirms it.
- Tests must use mocked provider calls.
- Failed messages must not undo invoice/payment state.

### 10. InboundSMS

Fields:
- `id`: UUID
- `provider_message_id`: stable AT message identifier
- `idempotency_key`: unique digest derived from provider and message ID
- `artist_id`: nullable FK to matched artist
- `sender`: normalized sender number
- `message_digest`: SHA-256 digest; raw SMS body is not retained
- `command`, `outcome`, `created_at`

Use this record to suppress provider retries and audit command outcome. Retain minimal personal data and apply an appropriate retention policy.

### 11. Optional Subscription / Plan
Not required for MVP unless a paid tier must be launched immediately. If introduced later:
- `artist_id`
- `plan_key`
- `status`
- provider subscription reference
- `current_period_start`, `current_period_end`
- timestamps

Do not implement subscription billing just to model the freemium idea.

## Derived values

- `invoice_amount_paid`: sum of eligible successful payments minus verified refunds, using the project's documented refund policy.
- `invoice_balance_due`: total amount minus net paid amount.
- `invoice_is_overdue`: issued and outstanding after due date, subject to timezone/date policy.
- `artist_revenue`: report by currency and date range; never sum different currencies without explicit conversion data and disclosure.

## Essential database constraints

- Foreign keys and deletion behaviour chosen to preserve financial history.
- Unique invoice number per artist.
- Unique provider reference/event identity where guaranteed.
- Positive invoice line quantities; non-negative prices under the selected policy.
- Positive payment amounts.
- Prevent cross-artist customer/project/invoice relationships through service validation and, where practical, database design/constraints.
- Index foreign keys and common dashboard filters.
- Use transactions and row locking/constraints where concurrent payment processing can cause overpayment or duplicate effects.

## Open schema decisions

- Custom user vs built-in user plus `ArtistProfile`.
- Manual payment entry policy.
- Exact invoice status strategy (computed vs stored).
- Refund representation and partial refunds.
- Token expiry and revocation rules.
- Initial currencies and rounding rules.
- Whether SMS consent/preferences are per artist-customer pair or stored in a shared contact model.
