"""
Tests for owner-scoping patterns.

Stage 1 has no customer/invoice/project models yet, so we verify the pattern
at the User / ArtistProfile level:
  - UUID primary keys are generated
  - Each user owns their own profile and cannot access another's
  - Filtering by user always returns only that user's records
"""
import pytest

from accounts.models import ArtistProfile, User


@pytest.mark.django_db
def test_user_has_uuid_primary_key(artist_user):
    """The custom User model uses a UUID as its primary key."""
    import uuid
    assert isinstance(artist_user.pk, uuid.UUID)


@pytest.mark.django_db
def test_artist_profile_auto_created_on_user_save(db):
    """Creating a User via create_user triggers the signal and creates an ArtistProfile."""
    user = User.objects.create_user(email="signal@example.com", password="pass1234!")
    assert ArtistProfile.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_profile_scoped_to_owner(artist_user, another_artist):
    """
    Querying ArtistProfile filtered by a specific user only returns that user's profile.
    This verifies the owner-scoping pattern: `ArtistProfile.objects.filter(user=request.user)`.
    """
    artist_profiles = ArtistProfile.objects.filter(user=artist_user)
    other_profiles = ArtistProfile.objects.filter(user=another_artist)

    # Each artist sees only their own profile
    assert artist_profiles.count() == 1
    assert artist_profiles.first().user == artist_user

    assert other_profiles.count() == 1
    assert other_profiles.first().user == another_artist

    # Artist A's filter excludes Artist B's profile
    assert not artist_profiles.filter(user=another_artist).exists()


@pytest.mark.django_db
def test_two_users_have_distinct_uuids(artist_user, another_artist):
    """Two distinct users must have different UUID primary keys."""
    assert artist_user.pk != another_artist.pk


@pytest.mark.django_db
def test_artist_profile_default_currency(artist_user):
    """ArtistProfile default_currency must be 'USD' unless overridden."""
    profile = artist_user.artist_profile
    assert profile.default_currency == "USD"


@pytest.mark.django_db
def test_profile_update_does_not_affect_other_user(artist_user, another_artist):
    """Modifying one artist's profile must not alter the other's."""
    profile = artist_user.artist_profile
    profile.business_name = "Artist One Studio"
    profile.save(update_fields=["business_name"])

    other_profile = another_artist.artist_profile
    other_profile.refresh_from_db()
    assert other_profile.business_name != "Artist One Studio"
