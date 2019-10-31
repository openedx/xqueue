# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('queue', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='arrival_time',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
