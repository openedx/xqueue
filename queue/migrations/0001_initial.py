# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime

from django.db import models, migrations, connection


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('requester_id', models.CharField(max_length=128)),
                ('lms_callback_url', models.CharField(max_length=128, db_index=True)),
                ('queue_name', models.CharField(max_length=128, db_index=True)),
                ('xqueue_header', models.CharField(max_length=1024)),
                ('xqueue_body', models.TextField()),
                ('s3_keys', models.CharField(max_length=1024)),
                ('s3_urls', models.CharField(max_length=1024)),
                ('arrival_time', models.DateTimeField(auto_now=True)),
                ('pull_time', models.DateTimeField(null=True, blank=True)),
                ('push_time', models.DateTimeField(null=True, blank=True)),
                ('return_time', models.DateTimeField(null=True, blank=True)),
                ('grader_id', models.CharField(max_length=128)),
                ('pullkey', models.CharField(max_length=128)),
                ('grader_reply', models.TextField()),
                ('num_failures', models.IntegerField(default=0)),
                ('lms_ack', models.BooleanField(default=False)),
                ('retired', models.BooleanField(default=False, db_index=True)),
            ],
        ),
    ]
