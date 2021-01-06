from django.db import migrations, models


class Migration(migrations.Migration):
    replaces = [('queue', '0002_stop_updating_arrival_time')]

    dependencies = [
        ('submission_queue', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='arrival_time',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
