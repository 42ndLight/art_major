"""
Forms for the accounts app.
"""
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

from .models import ArtistProfile, User

CURRENCY_CHOICES = [
    ("USD", "USD — US Dollar"),
    ("EUR", "EUR — Euro"),
    ("GBP", "GBP — British Pound"),
    ("KES", "KES — Kenyan Shilling"),
]


class SignUpForm(forms.Form):
    """Registration form — creates a User + ArtistProfile."""

    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email"}),
    )
    display_name = forms.CharField(
        label="Display name",
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Your name or artist alias"}),
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••", "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••", "autocomplete": "new-password"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned_data

    def save(self):
        """Create and return the new User (profile created via signal)."""
        user = User.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
        )
        # Update the auto-created profile's display_name
        profile = user.artist_profile
        profile.display_name = self.cleaned_data["display_name"]
        profile.save(update_fields=["display_name"])
        return user


class LoginForm(forms.Form):
    """Email + password login form."""

    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email"}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••", "autocomplete": "current-password"}),
    )

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        self._user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email", "").lower()
        password = cleaned_data.get("password")

        if email and password:
            user = authenticate(self.request, username=email, password=password)
            if user is None:
                raise forms.ValidationError("Invalid email or password. Please try again.")
            if not user.is_active:
                raise forms.ValidationError("This account is inactive.")
            self._user = user
        return cleaned_data

    def get_user(self):
        return self._user


class ProfileForm(forms.ModelForm):
    """Edit ArtistProfile details."""

    class Meta:
        model = ArtistProfile
        fields = ["display_name", "business_name", "default_currency", "timezone"]
        widgets = {
            "display_name": forms.TextInput(attrs={"placeholder": "Your public name"}),
            "business_name": forms.TextInput(attrs={"placeholder": "Studio or business name (optional)"}),
            "timezone": forms.TextInput(attrs={"placeholder": "e.g. Africa/Nairobi"}),
        }

    default_currency = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        label="Default currency",
    )
