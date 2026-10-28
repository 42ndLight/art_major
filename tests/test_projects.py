"""
Tests for Project/Commission management and boundaries.
"""
from decimal import Decimal
import pytest
from django.urls import reverse

from customers.models import Customer
from projects.models import Project, ProjectStatus


@pytest.mark.django_db
def test_artist_can_create_project(auth_client, artist_user):
    customer = Customer.objects.create(artist=artist_user, name="Gallery Host")
    url = reverse("projects:create")
    data = {
        "customer": str(customer.pk),
        "title": "Mural Commission",
        "description": "5x10m outdoor wall artwork",
        "agreed_amount": "2500.00",
        "currency": "USD",
        "due_date": "2026-12-31",
        "status": ProjectStatus.IN_PROGRESS,
    }
    response = auth_client.post(url, data)
    assert response.status_code == 302

    project = Project.objects.get(title="Mural Commission")
    assert project.artist == artist_user
    assert project.customer == customer
    assert project.agreed_amount == Decimal("2500.00")
    assert project.status == ProjectStatus.IN_PROGRESS


@pytest.mark.django_db
def test_project_status_transitions(auth_client, artist_user):
    customer = Customer.objects.create(artist=artist_user, name="Brand Co")
    project = Project.objects.create(
        artist=artist_user,
        customer=customer,
        title="Logo Illustration",
        status=ProjectStatus.INQUIRY,
    )
    assert project.completed_at is None

    # Change status to completed via status update endpoint
    url = reverse("projects:status_update", kwargs={"pk": project.pk})
    auth_client.post(url, {"status": ProjectStatus.COMPLETED})
    project.refresh_from_db()
    assert project.status == ProjectStatus.COMPLETED
    assert project.completed_at is not None


@pytest.mark.django_db
def test_project_owner_scoping(client, artist_user, another_artist):
    other_customer = Customer.objects.create(artist=another_artist, name="Other Client")
    other_project = Project.objects.create(
        artist=another_artist,
        customer=other_customer,
        title="Secret Album Art",
    )

    client.login(username="artist@example.com", password="testpass123")

    # Detail 404
    detail_resp = client.get(reverse("projects:detail", kwargs={"pk": other_project.pk}))
    assert detail_resp.status_code == 404

    # Status update 404
    status_resp = client.post(
        reverse("projects:status_update", kwargs={"pk": other_project.pk}),
        {"status": ProjectStatus.COMPLETED},
    )
    assert status_resp.status_code == 404
