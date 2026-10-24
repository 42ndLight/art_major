# Styling and UX Guide

## 1. Design objective

Create a clean, modern, professional, calm, and accessible workspace for independent artists. The interface should feel welcoming to creative users without looking like an art portfolio or social network. It is a business tool: clarity and trust come first.

Reference direction: light neutral backgrounds, clear typography, restrained blue primary actions, quiet borders, consistent spacing, subtle status colours, and useful artwork thumbnails only where they help users recognise a project.

## 2. Design principles

1. **Clarity over decoration:** Every screen should make its purpose and primary action obvious.
2. **User-focused language:** Use “Add customer”, “Create invoice”, “Amount due”, and “Payment confirmed”, not technical jargon.
3. **Progressive disclosure:** Show essential information first; place secondary details behind a clearly labelled section.
4. **Consistency:** Reuse the same form, table/list, badge, alert, button, and modal patterns.
5. **Accessible by default:** Semantic HTML, keyboard access, visible focus, sufficient contrast, and understandable errors.
6. **Mobile-first resilience:** Core workflows must work on a narrow phone screen, not merely shrink a desktop layout.
7. **Trustworthy money UI:** Always display currency, status text, and clear totals. Do not use colour as the only status indicator.
8. **No false affordances:** If something looks clickable, it must work.

## 3. Visual foundation

### Backgrounds and surfaces
- App background: very light neutral (e.g. `base-200`/a carefully chosen neutral token).
- Main content/card surfaces: white or `base-100`.
- Sidebar: may use a dark neutral on wide screens, but preserve strong contrast and a clear active item.
- Borders: subtle neutral borders, not heavy outlines around every element.
- Shadows: restrained; use mainly for elevated menus/dialogs, not every card.
- Avoid large gradients, glassmorphism, excessive blur, or decorative backgrounds behind dense business data.

### Colour
Use daisyUI semantic tokens where possible (`primary`, `secondary`, `accent`, `base-*`, `success`, `warning`, `error`, `info`) so themes can be changed consistently.

- Primary actions: clear blue or selected accessible primary colour.
- Success: confirmed/paid, always with text or icon plus colour.
- Warning: due soon, attention required.
- Error: failed, invalid, or overdue only where semantically correct.
- Neutral: draft, inactive, or informational states.

Never invent one-off colours in individual components without reason. Verify actual foreground/background combinations for WCAG contrast; do not assume default theme colours pass.

## 4. Typography

- Use a readable sans-serif stack and consistent type scale.
- Body text should be comfortable to read; target roughly 16px for ordinary text where layout permits.
- Labels should remain readable and visible.
- Use tabular numerals for financial totals when available.
- Use bold sparingly for hierarchy: page title, section heading, key amount, and primary status.
- Avoid long all-caps labels, tiny muted text, and light-weight text on pale backgrounds.
- Do not rely on placeholder text as the only form label.

## 5. Layout and spacing

- Use a consistent spacing scale based on Tailwind spacing tokens.
- Align page title, description, actions, filters, and content.
- Give forms sufficient vertical space and group related fields.
- Prefer a clear main content width and avoid overly wide text lines.
- Desktop may use sidebar plus content; mobile should use a compact header/navigation pattern.
- Tables should transform gracefully on small screens: allow horizontal scroll only when appropriate, or use stacked labelled cards.
- Keep key actions reachable and avoid sticky UI that covers content or keyboard focus.

## 6. Navigation

Primary artist navigation should stay focused:
- Dashboard
- Customers
- Projects
- Invoices
- Payments
- Communications (if relevant to MVP)
- Settings

Use descriptive labels and consistent icons. Icons must have text labels where ambiguity is possible. Show active navigation with more than a subtle colour change. Do not put infrequent settings above core business tasks.

## 7. Dashboard patterns

Show a small number of actionable summaries:
- Outstanding balance
- Confirmed payments over a clear date range
- Active projects
- Overdue invoices

Rules:
- Each metric must define its meaning.
- Clickable metrics should lead to a filtered list.
- Keep currencies separate; do not add USD and KES into one total without explicit conversion.
- Provide empty states with a useful next action, e.g. “No customers yet — add your first customer.”
- Avoid charts in the MVP unless they help a real decision.

## 8. Forms and validation

- Every input has a persistent visible label.
- Mark required fields clearly and explain formats where needed.
- Group fields logically; avoid huge forms.
- Display errors next to fields and provide a concise summary for longer forms.
- Do not clear safe user input after a validation error.
- Use correct input types, autocomplete attributes, and mobile-friendly controls.
- Use server-side validation regardless of client-side feedback.
- Confirm consequential actions such as voiding an issued invoice.
- Buttons must have clear action labels: “Save customer”, “Issue invoice”, “Send test SMS”.
- Distinguish primary, secondary, and destructive actions visually and semantically.

## 9. Invoice and payment UI

- Show invoice reference, artist/business, customer-facing description, issue/due dates, currency, total, paid amount, and remaining balance.
- Keep the public invoice page simple and fast, with no unnecessary navigation to the private artist dashboard.
- State the available payment methods only after checking provider support.
- Show pending, confirmed, failed, and refunded states with text labels and accessible icons.
- On return from checkout, display “Payment processing” until server verification confirms success.
- Provide a clear retry path after failure without creating duplicate charges.
- Show provider fees or conversion details when applicable and known; never imply an exchange rate that was not applied.
- Use a clear receipt and transaction reference after confirmation.

## 10. HTMX and Alpine behaviour

- Use HTMX for server-rendered partial updates, search, filtering, inline changes, and form submissions where useful.
- Keep URL behaviour and back/forward navigation understandable.
- Show loading and error feedback for asynchronous requests.
- Preserve or restore focus after a partial update when appropriate.
- Announce important status changes to assistive technology using suitable live regions.
- Use Alpine only for small local interactions; do not duplicate business rules in browser code.
- Ensure core functionality remains understandable when JavaScript is unavailable where practical.

## 11. Accessibility target

Aim for WCAG 2.2 AA as the design and testing target; verify applicability and actual conformance rather than claiming compliance without testing.

Checklist:
- Semantic landmarks and logical heading order.
- Keyboard operation for every interactive control.
- Visible focus indicator with adequate contrast.
- Text contrast of at least 4.5:1 for normal text and 3:1 for large text; non-text controls/focus indicators should meet applicable WCAG criteria.
- Do not use colour alone to communicate meaning.
- Useful accessible names for buttons and icon controls.
- Labels and error messages programmatically associated with inputs.
- Adequate target sizes, aiming for approximately 44×44 CSS pixels for common touch controls where practical.
- Reflow at narrow widths and usable browser zoom.
- Respect `prefers-reduced-motion`.
- Images have useful alt text when meaningful; decorative images have empty alt text.
- Do not rely on hover alone.
- Test with keyboard and at least one screen reader when feasible.

## 12. Components to standardise

Use Tailwind and daisyUI tokens/components where appropriate:
- Page header and breadcrumbs
- Sidebar/top navigation
- Buttons (primary, secondary, ghost, destructive)
- Inputs, selects, textareas, checkbox/radio controls
- Cards and summary metrics
- Status badges with text
- Tables/list rows
- Empty states
- Alerts/toasts
- Confirm dialogs
- Pagination/search/filter bars
- Invoice summary and payment timeline
- Responsive navigation

Review each daisyUI component's rendered semantics and keyboard behaviour. A component library is not proof of accessibility.

## 13. Avoid

- Tiny low-contrast secondary text.
- Icon-only actions without accessible names.
- Status conveyed only through red/green.
- Too many cards and metrics on one screen.
- Different button styles for the same action across pages.
- Decorative animations that slow down routine work.
- Destructive actions placed beside primary actions without distinction.
- Dense tables that become unusable on mobile.
- Placeholder-only labels.
- Fake data or charts presented as real account information.
