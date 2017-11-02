# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('queue_app', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='Submission',
            options=dict(
                db_table='queue_submission'
            ),
        ),
    ]
