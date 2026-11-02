"""Strict pipe-delimited SMS commands that write and update artist-scoped records."""
from decimal import Decimal, InvalidOperation

from django.db import transaction

from billing.models import Invoice, InvoiceLine, InvoiceStatus
from customers.models import Customer


HELP = (
    "Commands: CUSTOMER|Name|+254712345678 to create/update a client. "
    "INVOICE|Client Name|amount|KES|description to create a draft. "
    "INVOICE|INV-0001|amount|KES|description to update a draft."
)


def parse_and_execute(artist, text):
    parts = [part.strip() for part in text.split("|")]
    command = parts[0].upper() if parts else ""

    if command in ("CUSTOMER", "UPDATE_CUSTOMER") and len(parts) in (2, 3, 4):
        name = parts[1].strip()
        if not name:
            return "Add a customer name. " + HELP, "invalid"

        phone = ""
        email = ""
        if len(parts) >= 3:
            p2 = parts[2].strip()
            if "@" in p2:
                email = p2
            else:
                phone = p2
        if len(parts) == 4:
            p3 = parts[3].strip()
            if "@" in p3:
                email = p3
            elif not phone:
                phone = p3

        if phone and (not phone.startswith("+") or not phone[1:].isdigit() or len(phone) > 16):
            return "Use the customer's phone in international format, starting with +.", "invalid"

        with transaction.atomic():
            # Match customer case-insensitively for this artist
            customer = Customer.objects.filter(
                artist=artist,
                name__iexact=name[:255],
            ).first()

            if customer:
                updated_fields = []
                if customer.archived_at:
                    customer.archived_at = None
                    updated_fields.append("archived_at")
                if phone and customer.phone_number != phone:
                    customer.phone_number = phone
                    updated_fields.append("phone_number")
                if email and customer.email != email:
                    customer.email = email
                    updated_fields.append("email")

                if updated_fields:
                    updated_fields.append("updated_at")
                    customer.save(update_fields=updated_fields)
                    details = []
                    if phone:
                        details.append(f"phone {phone}")
                    if email:
                        details.append(f"email {email}")
                    detail_str = f" with {', '.join(details)}" if details else ""
                    return f"Customer {customer.name} updated{detail_str}.", "customer_updated"
                return f"Customer {customer.name} already exists.", "customer_exists"
            else:
                customer = Customer.objects.create(
                    artist=artist,
                    name=name[:255],
                    phone_number=phone,
                    email=email,
                )
                return f"Customer {customer.name} created.", "customer_created"

    if command in ("INVOICE", "UPDATE_INVOICE") and len(parts) == 5:
        _, target, amount_text, currency, description = parts
        target = target.strip()
        amount_text = amount_text.strip().replace(",", "")
        currency = currency.strip().upper()
        description = description.strip()

        if not all((target, amount_text, currency, description)):
            return "Include customer/invoice, amount, currency, and description. " + HELP, "invalid"

        try:
            amount = Decimal(amount_text)
        except InvalidOperation:
            return "Amount must be a number. " + HELP, "invalid"

        if (
            not amount.is_finite()
            or amount <= 0
            or amount >= Decimal("10000000000")
            or amount.as_tuple().exponent < -2
            or len(currency) != 3
            or not currency.isalpha()
        ):
            return "Use a positive amount (up to 2 decimals) and a 3-letter currency code.", "invalid"

        # Check if target is an existing invoice number for this artist
        existing_invoice = Invoice.objects.filter(
            artist=artist,
            invoice_number__iexact=target,
        ).first()

        if existing_invoice:
            if existing_invoice.status != InvoiceStatus.DRAFT:
                return (
                    f"Invoice {existing_invoice.invoice_number} is already {existing_invoice.get_status_display().lower()} and cannot be modified via SMS.",
                    "invoice_immutable",
                )
            with transaction.atomic():
                existing_invoice.currency = currency
                existing_invoice.save(update_fields=["currency", "updated_at"])
                line = existing_invoice.lines.first()
                if line:
                    line.description = description[:255]
                    line.unit_price = amount
                    line.quantity = Decimal("1.00")
                    line.save()
                else:
                    InvoiceLine.objects.create(
                        invoice=existing_invoice,
                        description=description[:255],
                        quantity=Decimal("1.00"),
                        unit_price=amount,
                    )
                existing_invoice.calculate_totals()
            return (
                f"Draft {existing_invoice.invoice_number} updated: {amount:.2f} {currency} for {existing_invoice.customer.name}. Review it in ArtMajor.",
                "invoice_draft_updated",
            )

        # Target is a customer name
        matching_customers = Customer.objects.filter(
            artist=artist,
            name__iexact=target,
            archived_at__isnull=True,
        )
        if not matching_customers.exists():
            return f"I couldn't find {target}. Create them first: CUSTOMER|{target}|+254...", "customer_missing"
        if matching_customers.count() > 1:
            return "More than one customer has that name. Rename one in ArtMajor, then try again.", "customer_ambiguous"

        customer = matching_customers.get()
        with transaction.atomic():
            invoice = Invoice.objects.create(
                artist=artist,
                customer=customer,
                invoice_number=Invoice.generate_next_number(artist),
                currency=currency,
            )
            InvoiceLine.objects.create(
                invoice=invoice,
                description=description[:255],
                quantity=Decimal("1.00"),
                unit_price=amount,
            )
            invoice.calculate_totals()
        return (
            f"Draft {invoice.invoice_number} saved: {amount:.2f} {currency} for {customer.name}. Review it in ArtMajor.",
            "invoice_draft_created",
        )

    return HELP, "help"
