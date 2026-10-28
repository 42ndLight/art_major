"""
Views for the accounts app.
"""
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

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
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("profile")
        return render(request, self.template_name, {"form": form, "profile": profile})
