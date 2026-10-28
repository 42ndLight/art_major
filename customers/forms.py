"""
Forms for Customer management.
"""
from django import forms
from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "email", "phone_number", "country", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "input input-bordered w-full",
                "placeholder": "e.g. Jane Doe or ACME Corp",
                "required": True,
            }),
            "email": forms.EmailInput(attrs={
                "class": "input input-bordered w-full",
                "placeholder": "client@example.com",
            }),
            "phone_number": forms.TextInput(attrs={
                "class": "input input-bordered w-full",
                "placeholder": "+1 555 123 4567",
            }),
            "country": forms.TextInput(attrs={
                "class": "input input-bordered w-full",
                "placeholder": "e.g. United States, Kenya, UK",
            }),
            "notes": forms.Textarea(attrs={
                "class": "textarea textarea-bordered w-full",
                "rows": 3,
                "placeholder": "Client preferences, background, or social links",
            }),
        }
