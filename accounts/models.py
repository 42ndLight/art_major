"""
Custom User model and ArtistProfile for the Artist Business Workspace.
"""
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models import Q


class UserManager(BaseUserManager):
    """Manager for the email-based custom User model."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Email-based user with UUID primary key."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email

    def get_full_name(self):
        try:
            return self.artist_profile.display_name
        except ArtistProfile.DoesNotExist:
            return self.email

    def get_short_name(self):
        return self.get_full_name()


class ArtistProfile(models.Model):
    """Extended profile for an artist/business owner."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="artist_profile",
    )
    display_name = models.CharField(max_length=150)
    business_name = models.CharField(max_length=200, blank=True)
    default_currency = models.CharField(max_length=3, default="USD")
    timezone = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=32, blank=True, db_index=True)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    sms_verification_code_hash = models.CharField(max_length=128, blank=True)
    sms_verification_expires_at = models.DateTimeField(null=True, blank=True)
    sms_verification_attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "artist profile"
        verbose_name_plural = "artist profiles"
        constraints = [
            models.UniqueConstraint(
                fields=["phone_number"],
                condition=~Q(phone_number=""),
                name="unique_nonempty_artist_sms_phone",
            ),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.user.email})"
