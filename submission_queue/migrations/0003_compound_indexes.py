# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submission_queue', '0002_stop_updating_arrival_time'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='submission',
            index_together=set([('queue_name', 'retired', 'pull_time', 'arrival_time'), ('lms_callback_url', 'retired'), ('queue_name', 'retired', 'push_time', 'arrival_time')]),
        ),
    ]
