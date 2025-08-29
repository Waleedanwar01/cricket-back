from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("book", "0004_add_status_payment_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="confirmation_token",
            field=models.CharField(max_length=128, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="book",
            name="confirmed_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]


