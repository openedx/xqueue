# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations, OperationalError
from django.db.utils import ProgrammingError


pinned_submission_table_name = 'queue_submission'
old_app_name = 'queue'
new_app_name = 'queue_app'


class CreateSubmissionModel(migrations.CreateModel):
    """
    This custom logic was needed to support the renaming of the 'queue' app to 'queue_app'. If the database is being
    built from scratch, this will behave like a normal migration and create the submission table. If migrations have
    already been applied using the old app name ('queue'), this initial migration will be run (since 'queue_app' does
    not yet exist in the migrations table) and will rename 'queue' to 'queue_app' in the appropriate Django database
    table columns. No table will be added, and it will not be renamed since we're keeping the name of the table from
    before the app name change.
    """
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        try:
            # Try to select from the submissions table
            schema_editor.execute("SELECT * FROM {}".format(pinned_submission_table_name))
        except (OperationalError, ProgrammingError):
            # An exception means that the submission table does not exist and we can create it
            super(CreateSubmissionModel, self).database_forwards(app_label, schema_editor, from_state, to_state)
        else:
            # If the query succeeds, the table already exists and we need to ensure that the new app name is reflected
            # in the appropriate Django database tables
            schema_editor.execute(
                "UPDATE django_content_type SET app_label = %s WHERE app_label = %s", [new_app_name, old_app_name]
            )
            schema_editor.execute(
                "UPDATE django_migrations SET app = %s WHERE app = %s", [new_app_name, old_app_name]
            )


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        CreateSubmissionModel(
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
            options=dict(
                db_table=pinned_submission_table_name
            ),
        )
    ]
