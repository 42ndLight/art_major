"""
Views for the accounts app.
"""
import secrets
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from communications.services import AfricaTalkingError, send_sms
from .forms import LoginForm, ProfileForm, SignUpForm


class SignUpView(View):
    """Create a new artist account."""

    template_name = "accounts/signup.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("dashboard")
        return render(request, self.template_name, {"form": SignUpForm()})

    def post(self, request):
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome! Your account has been created.")
            return redirect("dashboard")
        return render(request, self.template_name, {"form": form})


class LoginView(View):
    """Authenticate an existing artist."""

    template_name = "accounts/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("dashboard")
        return render(request, self.template_name, {"form": LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST, request=request)
        if form.is_valid():
            login(request, form.get_user())
            next_url = request.GET.get("next", "dashboard")
            return redirect(next_url)
        return render(request, self.template_name, {"form": form})


class LogoutView(View):
    """Sign out — POST only (CSRF protection)."""

    def post(self, request):
        logout(request)
        return redirect("login")

    def get(self, request):
        # Redirect GET requests to dashboard (or login)
        return redirect("dashboard" if request.user.is_authenticated else "login")


class ProfileView(LoginRequiredMixin, View):
    """Edit the authenticated artist's profile."""

    template_name = "accounts/profile.html"

    def get_profile(self, request):
        return request.user.artist_profile

    def get(self, request):
        profile = self.get_profile(request)
        form = ProfileForm(instance=profile)
        return render(request, self.template_name, {"form": form, "profile": profile})

    def post(self, request):
        profile = self.get_profile(request)
        action = request.POST.get("action")
        if action == "send_sms_code":
            phone = request.POST.get("phone_number", "").strip()
            if not phone.startswith("+") or not phone[1:].isdigit() or not 8 <= len(phone[1:]) <= 15:
                messages.error(request, "Enter a phone number in international format, for example +254712345678.")
                return redirect("profile")
            if profile.sms_verification_expires_at and profile.sms_verification_expires_at > timezone.now():
                messages.info(request, "A verification code was already sent. Use it or wait for it to expire before requesting another.")
                return redirect("profile")
            if ArtistProfile.objects.filter(phone_number=phone).exclude(pk=profile.pk).exists():
                messages.error(request, "That phone number is already linked to another artist account.")
                return redirect("profile")
            code = f"{secrets.randbelow(1_000_000):06d}"
            profile.phone_number = phone
            profile.phone_verified_at = None
            profile.sms_verification_code_hash = make_password(code)
            profile.sms_verification_expires_at = timezone.now() + timedelta(minutes=10)
            profile.sms_verification_attempts = 0
            profile.save(update_fields=["phone_number", "phone_verified_at", "sms_verification_code_hash", "sms_verification_expires_at", "sms_verification_attempts", "updated_at"])
            try:
                send_sms(phone, f"Your ArtMajor verification code is {code}. It expires in 10 minutes.")
            except AfricaTalkingError:
                profile.sms_verification_code_hash = ""
                profile.sms_verification_expires_at = None
                profile.save(update_fields=["sms_verification_code_hash", "sms_verification_expires_at", "updated_at"])
                messages.error(request, "Could not send a verification SMS. Check Africa's Talking configuration and try again.")
            else:
                messages.success(request, "Verification code sent. Enter it below within 10 minutes.")
            return redirect("profile")
        if action == "verify_sms_code":
            code = request.POST.get("verification_code", "").strip()
            if (profile.sms_verification_attempts < 5 and profile.sms_verification_code_hash and profile.sms_verification_expires_at
                    and profile.sms_verification_expires_at > timezone.now()
                    and check_password(code, profile.sms_verification_code_hash)):
                profile.phone_verified_at = timezone.now()
                profile.sms_verification_code_hash = ""
                profile.sms_verification_expires_at = None
                profile.sms_verification_attempts = 0
                profile.save(update_fields=["phone_verified_at", "sms_verification_code_hash", "sms_verification_expires_at", "sms_verification_attempts", "updated_at"])
                messages.success(request, "Phone verified. You can now send commands to ArtMajor by SMS.")
            else:
                if profile.sms_verification_code_hash and profile.sms_verification_attempts < 5:
                    profile.sms_verification_attempts += 1
                    if profile.sms_verification_attempts >= 5:
                        profile.sms_verification_code_hash = ""
                        profile.sms_verification_expires_at = None
                    profile.save(update_fields=["sms_verification_attempts", "sms_verification_code_hash", "sms_verification_expires_at", "updated_at"])
                messages.error(request, "That code is invalid or expired. Request a new one and try again.")
            return redirect("profile")
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            changed_phone = form.cleaned_data["phone_number"] != profile.phone_number
            new_phone = form.cleaned_data["phone_number"]
            if new_phone and ArtistProfile.objects.filter(phone_number=new_phone).exclude(pk=profile.pk).exists():
                form.add_error("phone_number", "That phone number is already linked to another artist account.")
                return render(request, self.template_name, {"form": form, "profile": profile})
            saved_profile = form.save(commit=False)
            if changed_phone:
                saved_profile.phone_verified_at = None
                saved_profile.sms_verification_code_hash = ""
                saved_profile.sms_verification_expires_at = None
                saved_profile.sms_verification_attempts = 0
            try:
                saved_profile.save()
            except IntegrityError as exc:
                if "unique_nonempty_artist_sms_phone" in str(exc):
                    form.add_error("phone_number", "That phone number is already linked to another artist account.")
                    return render(request, self.template_name, {"form": form, "profile": profile})
                raise
            messages.success(request, "Profile updated successfully.")
            return redirect("profile")
        return render(request, self.template_name, {"form": form, "profile": profile})
