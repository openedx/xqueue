# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Submission'
        db.create_table('queue_submission', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('requester_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('queue_name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('xqueue_header', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('xqueue_body', self.gf('django.db.models.fields.TextField')()),
            ('s3_keys', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('s3_urls', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('arrival_time', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('pull_time', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('push_time', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('return_time', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('grader_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('pullkey', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('grader_reply', self.gf('django.db.models.fields.TextField')()),
            ('num_failures', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('lms_ack', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('queue', ['Submission'])


    def backwards(self, orm):
        # Deleting model 'Submission'
        db.delete_table('queue_submission')


    models = {
        'queue.submission': {
            'Meta': {'object_name': 'Submission'},
            'arrival_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'grader_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'grader_reply': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lms_ack': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'num_failures': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pull_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'pullkey': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'push_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'queue_name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'requester_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'return_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            's3_keys': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            's3_urls': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'xqueue_body': ('django.db.models.fields.TextField', [], {}),
            'xqueue_header': ('django.db.models.fields.CharField', [], {'max_length': '1024'})
        }
    }

    complete_apps = ['queue']