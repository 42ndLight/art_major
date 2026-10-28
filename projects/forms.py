"""
Forms for Project/Commission management.
"""
from django import forms
from customers.models import Customer
from .models import Project, ProjectStatus


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "customer",
            "title",
            "description",
            "agreed_amount",
            "currency",
            "due_date",
            "status",
        ]
        widgets = {
            "customer": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "title": forms.TextInput(attrs={
                "class": "input input-bordered w-full",
                "placeholder": "e.g. Album Cover Illustration, Brand Identity",
                "required": True,
            }),
            "description": forms.Textarea(attrs={
                "class": "textarea textarea-bordered w-full",
                "rows": 4,
                "placeholder": "Commission brief, scope of work, deliverables, revisions...",
            }),
            "agreed_amount": forms.NumberInput(attrs={
                "class": "input input-bordered w-full",
                "step": "0.01",
                "placeholder": "0.00",
            }),
            "currency": forms.TextInput(attrs={
                "class": "input input-bordered w-full uppercase",
                "maxlength": "3",
            }),
            "due_date": forms.DateInput(attrs={
                "class": "input input-bordered w-full",
                "type": "date",
            }),
            "status": forms.Select(attrs={"class": "select select-bordered w-full"}),
        }

    def __init__(self, *args, artist=None, **kwargs):
        super().__init__(*args, **kwargs)
        if artist:
            self.fields["customer"].queryset = Customer.objects.filter(
                artist=artist
            ).active()
            # If editing an existing project with an archived customer, include that customer
            if self.instance and self.instance.pk and self.instance.customer_id:
                self.fields["customer"].queryset = Customer.objects.filter(
                    models_Q(artist=artist, archived_at__isnull=True)
                    | models_Q(pk=self.instance.customer_id)
                )
            if not self.instance.pk and hasattr(artist, "artist_profile"):
                self.fields["currency"].initial = artist.artist_profile.default_currency or "USD"


from django.db.models import Q as models_Q
