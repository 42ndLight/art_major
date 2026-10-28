"""
Signals for the accounts app.
Auto-create ArtistProfile when a new User is created.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ArtistProfile, User


@receiver(post_save, sender=User)
def create_artist_profile(sender, instance, created, **kwargs):
    """Create an ArtistProfile whenever a new User is saved for the first time."""
    if created:
        ArtistProfile.objects.get_or_create(
            user=instance,
            defaults={"display_name": instance.email.split("@")[0]},
        )
