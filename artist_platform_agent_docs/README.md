# Artist Business Workspace — Project Starter

A planning pack for a private business-management tool for independent artists. The initial audience is commission-based artists and designers. The product helps artists manage customers, projects, invoices, and payment status; it is not an art marketplace.

## Where the project is today

This folder is the whole project so far: it contains specifications, not an application. The first task is discovery and choosing the demo scope, then creating a runnable app. The answers mentioned by the project owner have not yet been captured in `research.md`; do not treat open questions there as decisions.

## Start here

1. Add the available project answers and evidence to `research.md`.
2. Review `roadmap.md` Stage 0 and settle the smallest testable first release.
3. Read `agent.md` and `rules.md` before implementation.
4. Use the remaining documents as provisional design guidance; confirm the stack and data model against the actual repository before building them.

## Intended first workflow

Artist signs in → adds a customer → tracks a commission → creates an invoice → shares a private invoice page → records or verifies payment → provides confirmation.

The customer should not need a platform account. Payment and communications behavior must be checked against target market and sandbox before production. Africa's Talking SMS commands are implemented on `feature-AT`; see `API.md` and `research.md` for current limitations.

## Document map

- `research.md` — user answers, evidence, unresolved questions, and decision log.
- `roadmap.md` — staged kickoff and acceptance criteria.
- `agent.md` — contributor workflow and approvals.
- `rules.md` — canonical engineering/security rules. `rule.md` remains a compatibility copy.
- `Architecture.md` — proposed system boundaries and workflows.
- `schema.md` / `erd.md` — proposed data model and relationships; keep aligned.
- `API.md` — proposed routes and integration contracts; not implemented routes.
- `styling_guide.md` — interface and accessibility direction.
- `review.md` — implementation review checklist.

## Source of truth

Product decisions and current stage belong in `research.md` and `roadmap.md`. `schema.md` describes the proposed data model; `API.md` describes proposed routes. These documents are not evidence that code or an integration exists. When documents disagree, resolve the decision and update all affected files before implementing it.
