# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        """By default, when the migration is run, all old entries are marked as being retired.
        However, entries that have not been pulled or pushed should not be marked this way -- 
        they represent submissions from the LMS that have yet to be passed onto a grader, either
        through the pull (Berkeley) or push (6.00x) mechanisms. We have to make sure these are 
        unretired. But we're only going to check things from the last day, since anything older
        than that is probably still retired but not properly marked because of a bug."""
        oldest_allowed_unretired = datetime.datetime.now() - datetime.timedelta(days=1)
        sql = "update queue_submission set retired=0 where pull_time is null and push_time is null " + \
              "and arrival_time > '{0}'".format(oldest_allowed_unretired.strftime('%Y-%m-%d %H:%M:%S'))
        db.execute(sql)

    def backwards(self, orm):
        raise RuntimeError("Cannot reverse this migration.")

    models = {
        'queue.submission': {
            'Meta': {'object_name': 'Submission'},
            'arrival_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'grader_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'grader_reply': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lms_ack': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'lms_callback_url': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'num_failures': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pull_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'pullkey': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'push_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'queue_name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'requester_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'retired': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'return_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            's3_keys': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            's3_urls': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'xqueue_body': ('django.db.models.fields.TextField', [], {}),
            'xqueue_header': ('django.db.models.fields.CharField', [], {'max_length': '1024'})
        }
    }

    complete_apps = ['queue']
    symmetrical = True
