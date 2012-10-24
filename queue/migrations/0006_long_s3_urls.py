# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Submission.s3_urls'
        db.alter_column('queue_submission', 's3_urls', self.gf('django.db.models.fields.TextField')())

        # Changing field 'Submission.s3_keys'
        db.alter_column('queue_submission', 's3_keys', self.gf('django.db.models.fields.TextField')())

    def backwards(self, orm):

        # Changing field 'Submission.s3_urls'
        db.alter_column('queue_submission', 's3_urls', self.gf('django.db.models.fields.CharField')(max_length=1024))

        # Changing field 'Submission.s3_keys'
        db.alter_column('queue_submission', 's3_keys', self.gf('django.db.models.fields.CharField')(max_length=1024))

    models = {
        'queue.submission': {
            'Meta': {'object_name': 'Submission'},
            'arrival_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'grader_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'grader_reply': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lms_ack': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'lms_callback_url': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'num_failures': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pull_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'pullkey': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'push_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'queue_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'requester_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'retired': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'return_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            's3_keys': ('django.db.models.fields.TextField', [], {}),
            's3_urls': ('django.db.models.fields.TextField', [], {}),
            'xqueue_body': ('django.db.models.fields.TextField', [], {}),
            'xqueue_header': ('django.db.models.fields.CharField', [], {'max_length': '1024'})
        }
    }

    complete_apps = ['queue']