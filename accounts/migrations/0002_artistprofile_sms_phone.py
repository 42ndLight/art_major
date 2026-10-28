from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="artistprofile",
            name="phone_number",
            field=models.CharField(blank=True, db_index=True, max_length=32),
        ),
        migrations.AddField(
            model_name="artistprofile",
            name="phone_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="artistprofile",
            name="sms_verification_code_hash",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="artistprofile",
            name="sms_verification_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="artistprofile",
            name="sms_verification_attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddConstraint(
            model_name="artistprofile",
            constraint=models.UniqueConstraint(
                condition=~Q(phone_number=""),
                fields=("phone_number",),
                name="unique_nonempty_artist_sms_phone",
            ),
        ),
    ]
