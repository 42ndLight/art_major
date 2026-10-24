# ERD and User UML

This document explains entity relationships and user-facing use cases. Keep it aligned with `schema.md`.

## 1. Entity relationship diagram

```mermaid
erDiagram
    ARTIST ||--o{ CUSTOMER : manages
    ARTIST ||--o{ PROJECT : owns
    ARTIST ||--o{ INVOICE : issues
    ARTIST ||--o{ PAYMENT : receives
    ARTIST ||--o{ COMMUNICATION_PREFERENCE : configures
    ARTIST ||--o{ COMMUNICATION_MESSAGE : sends

    CUSTOMER ||--o{ PROJECT : requests
    CUSTOMER ||--o{ INVOICE : receives
    CUSTOMER ||--o{ COMMUNICATION_PREFERENCE : has
    CUSTOMER ||--o{ COMMUNICATION_MESSAGE : receives

    PROJECT o|--o{ INVOICE : billed_by
    INVOICE ||--|{ INVOICE_LINE : contains
    INVOICE ||--o{ PAYMENT : paid_by
    PAYMENT ||--o{ PAYMENT_EVENT : records
    INVOICE o|--o{ COMMUNICATION_MESSAGE : references

    ARTIST {
      uuid id PK
      string email
      string display_name
      string business_name
      string default_currency
    }
    CUSTOMER {
      uuid id PK
      uuid artist_id FK
      string name
      string email
      string phone_number
      text notes
    }
    PROJECT {
      uuid id PK
      uuid artist_id FK
      uuid customer_id FK
      string title
      decimal agreed_amount
      string currency
      string status
      date due_date
    }
    INVOICE {
      uuid id PK
      uuid artist_id FK
      uuid customer_id FK
      uuid project_id FK
      string invoice_number
      string currency
      decimal total_amount
      string status
      string public_token_digest
    }
    INVOICE_LINE {
      uuid id PK
      uuid invoice_id FK
      string description
      decimal quantity
      decimal unit_price
      decimal line_total
    }
    PAYMENT {
      uuid id PK
      uuid artist_id FK
      uuid invoice_id FK
      string provider
      string provider_reference
      decimal amount
      string currency
      string status
    }
    PAYMENT_EVENT {
      uuid id PK
      uuid payment_id FK
      string provider
      string external_event_id
      string processing_status
    }
    COMMUNICATION_PREFERENCE {
      uuid id PK
      uuid artist_id FK
      uuid customer_id FK
      string channel
      boolean transactional_enabled
      string consent_status
    }
    COMMUNICATION_MESSAGE {
      uuid id PK
      uuid artist_id FK
      uuid customer_id FK
      uuid invoice_id FK
      string channel
      string purpose
      string status
    }
```

### Relationship notes

- An artist manages many customers and owns many projects, invoices, payments, and communication records.
- A customer can have many projects and invoices. A customer record is scoped to one artist in the MVP.
- A project belongs to one artist and one customer. It may have zero or more invoices.
- An invoice belongs to one artist and one customer, and may optionally relate to a project.
- An invoice contains one or more line items after it is issued.
- An invoice can have multiple payment attempts/records to support deposits and instalments.
- A payment can have multiple provider events. The provider event identity must be deduplicated where the provider supplies stable IDs.
- Communication preferences and messages are tied to the artist-customer relationship. A failed SMS does not alter payment status.
- Enforce same-artist relationships. A foreign key alone does not automatically guarantee that the referenced customer and invoice share the same artist.

## 2. Artist use-case UML

```mermaid
flowchart LR
    Artist([Artist])
    Customer([Customer without account])
    AT([Africa's Talking])
    Pay([Payment provider])

    UC1([Register and manage profile])
    UC2([Manage customers])
    UC3([Manage projects])
    UC4([Create invoice])
    UC5([Share private payment link])
    UC6([View dashboard and balances])
    UC7([Configure transactional messages])
    UC8([Receive invoice or project SMS])
    UC9([Open invoice link])
    UC10([Pay invoice])
    UC11([Receive receipt])

    Artist --> UC1
    Artist --> UC2
    Artist --> UC3
    Artist --> UC4
    Artist --> UC5
    Artist --> UC6
    Artist --> UC7
    Customer --> UC9
    Customer --> UC10
    Customer --> UC11
    UC7 --> AT
    UC8 --> AT
    UC10 --> Pay
    Pay --> UC6
    Pay --> UC11
```

## 3. Role-based workflow summary

### Artist
- Authenticated access to own dashboard and records.
- Create/edit customers, projects, invoices, and supported payment requests.
- View payment reconciliation and communication status.
- Revoke private links where supported.
- Never access another artist's private records.

### Customer
- No platform account required.
- Access only the invoice data exposed by a valid private token.
- Initiate payment through the supported provider flow.
- View confirmation/receipt for their transaction.
- Cannot access artist dashboard, other invoices, or internal notes.

### External providers
- Payment provider processes the payment and provides verified server-side evidence.
- Africa's Talking sends communication through the supported API.
- Provider acceptance is not equivalent to confirmed payment or guaranteed SMS delivery.

## 4. Consistency checks

Whenever the data model changes:
1. Update `schema.md`.
2. Update the ERD and relationship notes here.
3. Update `API.md` if exposed behaviour changes.
4. Add/update migration and tests.
5. Record significant trade-offs in `research.md`.
