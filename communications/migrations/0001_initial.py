import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="InboundSMS",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider_message_id", models.CharField(blank=True, max_length=120)),
                ("idempotency_key", models.CharField(max_length=64, unique=True)),
                ("sender", models.CharField(max_length=32)),
                ("message_digest", models.CharField(max_length=64)),
                ("command", models.CharField(blank=True, max_length=20)),
                ("outcome", models.CharField(default="received", max_length=30)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("artist", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
