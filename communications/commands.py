"""Strict pipe-delimited SMS commands that write only artist-scoped records."""
from decimal import Decimal, InvalidOperation

from django.db import transaction

from billing.models import Invoice, InvoiceLine
from customers.models import Customer


HELP = "Use CUSTOMER|Name|+254712345678 or INVOICE|Customer name|amount|KES|description. Invoices are saved as drafts."


def parse_and_execute(artist, text):
    parts = [part.strip() for part in text.split("|")]
    command = parts[0].upper() if parts else ""

    if command == "CUSTOMER" and len(parts) in (2, 3):
        _, name, *phone_parts = parts
        if not name:
            return "Add a customer name. " + HELP, "invalid"
        phone = phone_parts[0] if phone_parts else ""
        if phone and (not phone.startswith("+") or not phone[1:].isdigit() or len(phone) > 16):
            return "Use the customer's phone in international format, starting with +.", "invalid"
        with transaction.atomic():
            customer, created = Customer.objects.get_or_create(
                artist=artist,
                name=name[:255],
                defaults={"phone_number": phone},
            )
            if not created and phone and not customer.phone_number:
                customer.phone_number = phone
                customer.save(update_fields=["phone_number", "updated_at"])
        return f"Customer {customer.name} {'created' if created else 'already exists'}.", "customer_created" if created else "customer_exists"

    if command == "INVOICE" and len(parts) == 5:
        _, customer_name, amount_text, currency, description = parts
        if not all((customer_name, amount_text, currency, description)):
            return "Include customer, amount, currency, and description. " + HELP, "invalid"
        try:
            amount = Decimal(amount_text)
        except InvalidOperation:
            return "Amount must be a number. " + HELP, "invalid"
        if not amount.is_finite() or amount <= 0 or amount >= Decimal("10000000000") or amount.as_tuple().exponent < -2 or len(currency) != 3 or not currency.isalpha():
            return "Use a positive amount (up to 2 decimals) and a 3-letter currency code.", "invalid"
        matching_customers = Customer.objects.filter(
            artist=artist,
            name__iexact=customer_name,
            archived_at__isnull=True,
        )
        if not matching_customers.exists():
            return f"I couldn't find {customer_name}. Create them first: CUSTOMER|{customer_name}|+254...", "customer_missing"
        if matching_customers.count() > 1:
            return "More than one customer has that name. Rename one in ArtMajor, then try again.", "customer_ambiguous"
        customer = matching_customers.get()
        with transaction.atomic():
            invoice = Invoice.objects.create(
                artist=artist,
                customer=customer,
                invoice_number=Invoice.generate_next_number(artist),
                currency=currency.upper(),
            )
            InvoiceLine.objects.create(
                invoice=invoice,
                description=description[:255],
                quantity=Decimal("1.00"),
                unit_price=amount,
            )
            invoice.calculate_totals()
        return f"Draft {invoice.invoice_number} saved: {amount:.2f} {currency.upper()} for {customer.name}. Review it in ArtMajor.", "invoice_draft_created"

    return HELP, "help"
