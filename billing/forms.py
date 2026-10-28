"""
Forms for Invoices, Line Items, and Payments.
"""

from decimal import Decimal

from django import forms
from django.forms import inlineformset_factory

from customers.models import Customer
from projects.models import Project

from .models import Invoice, InvoiceLine, Payment


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            "customer",
            "project",
            "invoice_number",
            "currency",
            "issue_date",
            "due_date",
            "discount_amount",
            "notes",
        ]
        widgets = {
            "customer": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "project": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "invoice_number": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full font-mono",
                    "placeholder": "INV-0001",
                    "required": True,
                }
            ),
            "currency": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full uppercase",
                    "maxlength": "3",
                }
            ),
            "issue_date": forms.DateInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "type": "date",
                }
            ),
            "due_date": forms.DateInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "type": "date",
                }
            ),
            "discount_amount": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "step": "0.01",
                    "min": "0.00",
                    "placeholder": "0.00",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "textarea textarea-bordered w-full",
                    "rows": 3,
                    "placeholder": "Payment terms, bank details, or delivery notes...",
                }
            ),
        }

    def __init__(self, *args, artist=None, **kwargs):
        super().__init__(*args, **kwargs)
        if artist:
            self.instance.artist = artist
            self.fields["customer"].queryset = Customer.objects.filter(
                artist=artist
            ).active()
            self.fields["project"].queryset = Project.objects.filter(artist=artist)
            self.fields["project"].required = False

            if not self.instance.pk:
                self.fields["invoice_number"].initial = Invoice.generate_next_number(
                    artist
                )
                if hasattr(artist, "artist_profile"):
                    self.fields["currency"].initial = (
                        artist.artist_profile.default_currency or "USD"
                    )


class InvoiceLineForm(forms.ModelForm):
    class Meta:
        model = InvoiceLine
        fields = ["description", "quantity", "unit_price"]
        widgets = {
            "description": forms.TextInput(
                attrs={
                    "class": "input input-bordered input-sm w-full",
                    "placeholder": "Item / Service description",
                    "required": True,
                }
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "class": "input input-bordered input-sm w-full",
                    "step": "0.01",
                    "min": "0.01",
                    "value": "1.00",
                    "required": True,
                }
            ),
            "unit_price": forms.NumberInput(
                attrs={
                    "class": "input input-bordered input-sm w-full",
                    "step": "0.01",
                    "min": "0.00",
                    "placeholder": "0.00",
                    "required": True,
                }
            ),
        }


InvoiceLineFormSet = inlineformset_factory(
    Invoice,
    InvoiceLine,
    form=InvoiceLineForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class ManualPaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "payment_method", "notes"]
        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "step": "0.01",
                    "min": "0.01",
                    "required": True,
                }
            ),
            "payment_method": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "e.g. Bank Transfer, Cash, PayPal, M-Pesa",
                }
            ),
            "notes": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "Optional transaction note or reference",
                }
            ),
        }
