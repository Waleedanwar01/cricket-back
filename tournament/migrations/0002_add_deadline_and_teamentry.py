from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("tournament", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="tournament",
            name="registration_deadline",
            field=models.DateField(default="2099-12-31"),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="tournament",
            name="status",
            field=models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('booked', 'Booked'), ('cancelled', 'Cancelled')], default='pending', max_length=20),
        ),
        migrations.CreateModel(
            name="TeamEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("team_name", models.CharField(max_length=120)),
                ("contact_phone", models.CharField(blank=True, max_length=20)),
                ("status", models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("captain", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="team_entries", to="auth.user")),
                ("tournament", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="entries", to="tournament.tournament")),
            ],
        ),
    ]


