# Roadmap — Artist Business Workspace

## Product goal

Help independent commission-based artists keep client work and getting paid in one place. The first release is a private business tool, not a marketplace. Keep the demo focused on one end-to-end workflow.

## Current status

**Stage: kickoff / discovery.** This repository currently contains planning documents only; there is no runnable application. No external provider, event requirement, target country, or deadline has been verified. See `research.md` before treating any proposed integration as a commitment.

## Stage 0 — Turn the brief into decisions

- [ ] Add the user-provided answers to `research.md` (event, deadline, user, target country, device, time/team constraints).
- [ ] Review the official event brief and judging rubric, if this is for a hackathon.
- [ ] Pick the first user and the single demo workflow.
- [ ] Decide whether Django/PostgreSQL is a firm constraint or a proposal.
- [ ] Verify the required Africa's Talking product and sandbox path, if applicable.
- [ ] Research payment options only after choosing a target country and currency.
- [ ] Record choices and unresolved questions in the decision log.

**Exit:** the first release has a named user, a testable scope, and no unverified dependency in its critical path.

## Stage 1 — Make the project runnable

- [ ] Create the application scaffold and document local setup.
- [ ] Add base layout, navigation, responsive styles, and an empty dashboard.
- [ ] Add artist registration/sign-in and establish owner-scoped data access.
- [ ] Add project configuration, environment example, and a minimal health check.
- [ ] Add a small set of meaningful tests and the actual check/run commands.

**Exit:** a new contributor can run the app locally and sign in without needing production credentials.

## Stage 2 — Deliver the core workflow

- [x] Create and manage customers.
- [x] Create and update commissions/projects linked to customers.
- [x] Create invoice drafts with line items and server-calculated totals.
- [x] Issue an invoice and display it through a private, revocable customer link.
- [x] Show invoice state and record a payment only through the verified chosen flow (or clearly label a demo stub if payment research is incomplete).
- [x] Add a receipt/confirmation view only after payment evidence is verified.

**Exit:** an artist can complete the core workflow with test data; customer links reveal only intended invoice details; one artist cannot access another artist's records.

## Stage 3 — Add verified communications and payment integration

- [x] Implement only the payment provider and Africa's Talking channel supported by completed research.
- [x] Use sandbox credentials and test destinations; keep secrets out of source control.
- [x] Verify callbacks/transactions server-side and make event processing idempotent.
- [x] Record communication status and handle failures without undoing financial state.
- [x] Follow the documented consent and opt-out policy.
- [x] Prepare a safe, repeatable demo and list provider limitations clearly.

**Exit:** the integration matches official docs and the event brief; repeated events do not duplicate payments or messages; no real communication is sent unintentionally.

## Stage 4 — Pilot and polish

- [ ] Check mobile layouts, keyboard operation, labels, focus, contrast, and error states.
- [ ] Validate totals, balances, and currencies across the complete workflow.
- [ ] Run configured checks and record the exact results.
- [ ] Walk through the demo using realistic, non-sensitive data.
- [ ] Record remaining gaps and choose the next milestone from user feedback.

## First demo acceptance criteria

- [ ] Artist can sign in and manage a customer.
- [ ] Artist can create a project and an invoice with correct totals.
- [ ] Customer can open the private invoice page without an account.
- [ ] Invoice/payment state is clear and based on the implemented evidence source.
- [ ] Ownership boundaries prevent cross-artist access.
- [ ] Any provider feature shown in the demo is verified, sandboxed, and accurately described.
- [ ] The app can be started from documented instructions.

## Later, only after the core workflow works

Advanced analytics, custom branding, reminders, recurring invoices, additional markets/providers, customer accounts, subscriptions/Pro billing, team access, marketplace features, and AI features.

## Planning rule

Keep the current milestone small enough to finish. Move an item forward only when its acceptance evidence exists. Provider research and user answers live in `research.md`; model details live in `schema.md`; implementation contracts live in `API.md`.
