from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tournament", "0002_add_deadline_and_teamentry"),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='holder_phone',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='tournament',
            name='prize_money',
            field=models.PositiveIntegerField(default=0),
        ),
    ]


