"""
Shared fixtures for the test suite.
"""
import pytest
from django.test import Client

from accounts.models import ArtistProfile, User


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def artist_user(db):
    """A fully-formed artist user with a profile."""
    user = User.objects.create_user(email="artist@example.com", password="testpass123")
    # Signal auto-creates the profile; update display_name for clarity
    profile = user.artist_profile
    profile.display_name = "Test Artist"
    profile.save(update_fields=["display_name"])
    return user


@pytest.fixture
def another_artist(db):
    """A second artist — used to verify owner-scoping."""
    user = User.objects.create_user(email="other@example.com", password="testpass456")
    profile = user.artist_profile
    profile.display_name = "Other Artist"
    profile.save(update_fields=["display_name"])
    return user


@pytest.fixture
def auth_client(client, artist_user):
    """A test client already logged in as artist_user."""
    logged_in = client.login(username="artist@example.com", password="testpass123")
    assert logged_in, "Test setup failed: could not log in as artist@example.com"
    return client
