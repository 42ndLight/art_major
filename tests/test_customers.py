"""
Tests for Customer management and owner scoping.
"""
import pytest
from django.urls import reverse

from customers.models import Customer


@pytest.mark.django_db
def test_artist_can_create_customer(auth_client, artist_user):
    url = reverse("customers:create")
    data = {
        "name": "Acme Studios",
        "email": "acme@example.com",
        "phone_number": "+1 555 9876",
        "country": "Kenya",
        "notes": "Prefers vector assets",
    }
    response = auth_client.post(url, data)
    assert response.status_code == 302

    customer = Customer.objects.get(name="Acme Studios")
    assert customer.artist == artist_user
    assert customer.email == "acme@example.com"
    assert customer.country == "Kenya"


@pytest.mark.django_db
def test_artist_can_list_and_search_customers(auth_client, artist_user):
    Customer.objects.create(artist=artist_user, name="Alice In Wonderland", email="alice@test.com")
    Customer.objects.create(artist=artist_user, name="Bob The Builder", email="bob@test.com")

    # List all
    response = auth_client.get(reverse("customers:list"))
    assert response.status_code == 200
    assert "Alice In Wonderland" in response.content.decode()
    assert "Bob The Builder" in response.content.decode()

    # Search
    search_response = auth_client.get(reverse("customers:list") + "?q=Alice")
    assert "Alice In Wonderland" in search_response.content.decode()
    assert "Bob The Builder" not in search_response.content.decode()


@pytest.mark.django_db
def test_artist_can_archive_and_restore_customer(auth_client, artist_user):
    customer = Customer.objects.create(artist=artist_user, name="Temporary Client")
    assert not customer.is_archived

    archive_url = reverse("customers:archive", kwargs={"pk": customer.pk})
    auth_client.post(archive_url)
    customer.refresh_from_db()
    assert customer.is_archived

    # Active list hides archived
    active_resp = auth_client.get(reverse("customers:list"))
    assert customer not in active_resp.context["customers"]

    # Archived filter shows it
    archived_resp = auth_client.get(reverse("customers:list") + "?archived=1")
    assert customer in archived_resp.context["customers"]

    # Restore
    auth_client.post(archive_url)
    customer.refresh_from_db()
    assert not customer.is_archived


@pytest.mark.django_db
def test_customer_owner_scoping(client, artist_user, another_artist):
    # Customer owned by another artist
    other_customer = Customer.objects.create(artist=another_artist, name="Secret Client")

    # Log in as artist_user
    client.login(username="artist@example.com", password="testpass123")

    # Cannot view detail (404)
    detail_resp = client.get(reverse("customers:detail", kwargs={"pk": other_customer.pk}))
    assert detail_resp.status_code == 404

    # Cannot edit (404)
    edit_resp = client.post(
        reverse("customers:edit", kwargs={"pk": other_customer.pk}),
        {"name": "Hacked Name"},
    )
    assert edit_resp.status_code == 404
    other_customer.refresh_from_db()
    assert other_customer.name == "Secret Client"

    # Cannot archive (404)
    archive_resp = client.post(reverse("customers:archive", kwargs={"pk": other_customer.pk}))
    assert archive_resp.status_code == 404
    other_customer.refresh_from_db()
    assert not other_customer.is_archived
