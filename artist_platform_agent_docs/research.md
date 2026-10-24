# Research and Product Decisions

This file separates user intent from assumptions and verified external facts. Record sources before implementing payment, messaging, legal, or provider-specific behaviour.

## Current state

- **Verified from the project notes:** This is a business workspace for independent artists, initially focused on commission-based artists and designers. It is not a marketplace.
- **Verified from the project notes:** The intended core journey is artist → customer → project → invoice → customer invoice page → payment status/receipt.
- **User-provided answers:** None are recorded in this folder yet. The previous contents were questions and templates rather than answers. Add answers below as they become available.
- **Not verified:** Hackathon brief, judging criteria, deadline, Africa's Talking channel/API requirements, payment provider, launch country/currencies, and hosting.
- **Project status:** Documentation only. No application code or runnable project exists in this repository yet.

## Decision log

| ID | Decision | Status | Evidence / reason | Revisit when |
|---|---|---|---|---|
| D-001 | Start with a private business-management tool for commission-based artists/designers; do not build a marketplace. | Proposed | Product direction in the project notes. | User changes target or business model. |
| D-002 | Customers should be able to view an invoice from a private link without creating an account. | Proposed | Product direction in the project notes. | Usability or security research changes the flow. |
| D-003 | Build one complete customer-to-invoice path before expanding into analytics, plans, or automation. | Recommended | Keeps the first release demonstrable and small. | A confirmed event brief requires a different demo. |
| D-004 | Treat Africa's Talking as a possible required integration, but do not select a channel until the event brief confirms it. | Unresolved | No event brief or official API evidence is recorded. | Official brief and account sandbox are reviewed. |
| D-005 | Do not select or promise a payment provider until artist eligibility, country, currency, settlement, and verification flow are checked. | Unresolved | No provider research is recorded. | Target market and provider evidence are available. |

## Questions to answer first

### Product and event

1. What is the official event name, brief, deadline, rubric, and demo format?
2. Is Africa's Talking mandatory? Which product/channel must the demo use?
3. Who is the first real user: which country, artist type, and device?
4. What is the one workflow the first demo must prove?

### Payments and communications

1. Which provider can onboard the intended artist in the first launch country, and how does settlement work?
2. Which currencies and payment methods are required for the first demo?
3. Is sandbox acceptable for judging, and which test destination/sender setup is available?
4. Which transactional messages are needed, and what consent/opt-out rules apply?

### Build constraints

1. Where will the app be hosted and demonstrated?
2. Is Django/PostgreSQL already a constraint, or is the stack still open?
3. What is the available build time and team capacity?

## Research queue

| Priority | Research item | Required evidence | Blocks |
|---|---|---|---|
| P0 | Actual hackathon requirements | Official brief, rubric, deadline, demo rules | Hackathon scope and integration choice |
| P0 | First-user and launch-market choice | User answer or interview notes | Payment and UX choices |
| P0 | Africa's Talking flow | Current official docs plus sandbox experiment for the required channel | Messaging implementation |
| P0 | Payment provider fit | Official country/currency/onboarding docs and verified sandbox flow | Payment implementation |
| P1 | Hosting and deployment | Current platform constraints and environment requirements | Deployment setup |
| P1 | Framework/tool versions | Official docs and project setup once a repository exists | Dependency selection |

## Evidence entry template

Copy this for each external finding:

```text
ID: R-001
Question:
Finding:
Evidence type: Official documentation / event brief / user interview / experiment
Source title:
URL:
Access date:
Applies to: Country, account type, API version, environment
Confidence: High / Medium / Low
Decision affected:
Follow-up:
```

Use official provider/framework docs and the actual event brief for technical or event claims. Distinguish facts from interpretation. Never put credentials, customer contact details, or private invoice links here.

## Implementation gate

Before implementing payments or messages, record: the target country, selected provider/channel, official source URLs, sandbox result, callback or delivery behaviour, consent assumptions, and demo limits. Until then, keep those features as explicit stubs or defer them; never make up endpoints or claim support.
