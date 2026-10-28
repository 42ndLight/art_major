"""
Tests for authentication flows: sign-up, login, logout, and dashboard access.
"""
import pytest
from django.urls import reverse

from accounts.models import ArtistProfile, User


@pytest.mark.django_db
def test_signup_creates_user_and_profile(client):
    """POSTing valid data to /accounts/signup/ creates a User and an ArtistProfile."""
    url = reverse("signup")
    payload = {
        "email": "newartist@example.com",
        "display_name": "New Artist",
        "password1": "SuperSecret99!",
        "password2": "SuperSecret99!",
    }
    response = client.post(url, data=payload)

    # Should redirect to dashboard after success
    assert response.status_code == 302
    assert response["Location"] == reverse("dashboard")

    # User created
    assert User.objects.filter(email="newartist@example.com").exists()

    # Profile created and linked
    user = User.objects.get(email="newartist@example.com")
    assert hasattr(user, "artist_profile")
    assert user.artist_profile.display_name == "New Artist"


@pytest.mark.django_db
def test_signup_rejects_duplicate_email(client, artist_user):
    """A second sign-up attempt with an existing email must fail."""
    url = reverse("signup")
    payload = {
        "email": "artist@example.com",  # already registered via fixture
        "display_name": "Duplicate",
        "password1": "SuperSecret99!",
        "password2": "SuperSecret99!",
    }
    response = client.post(url, data=payload)
    assert response.status_code == 200  # stays on page with errors
    assert b"already exists" in response.content


@pytest.mark.django_db
def test_login_redirects_to_dashboard(client, artist_user):
    """Posting valid credentials to /accounts/login/ redirects to /dashboard/."""
    url = reverse("login")
    response = client.post(url, {"email": "artist@example.com", "password": "testpass123"})
    assert response.status_code == 302
    assert response["Location"] == reverse("dashboard")


@pytest.mark.django_db
def test_login_rejects_bad_credentials(client, artist_user):
    """Wrong password keeps the user on the login page with an error."""
    url = reverse("login")
    response = client.post(url, {"email": "artist@example.com", "password": "wrongpassword"})
    assert response.status_code == 200
    assert b"Invalid email or password" in response.content


@pytest.mark.django_db
def test_logout_redirects_to_login(auth_client):
    """POSTing to /accounts/logout/ redirects to the login page."""
    url = reverse("logout")
    response = auth_client.post(url)
    assert response.status_code == 302
    assert response["Location"] == reverse("login")


@pytest.mark.django_db
def test_dashboard_requires_login(client):
    """Unauthenticated GET to /dashboard/ redirects to login."""
    url = reverse("dashboard")
    response = client.get(url)
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_authenticated_dashboard_returns_200(auth_client):
    """An authenticated artist can access the dashboard."""
    url = reverse("dashboard")
    response = auth_client.get(url)
    assert response.status_code == 200
    assert b"Dashboard" in response.content
