# Generated by Django 5.2.3 on 2025-06-25 06:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('submission_queue', '0004_remove_queue_name_index'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='submission',
            new_name='queue_submi_queue_n_4c6cd5_idx',
            old_fields=('queue_name', 'retired', 'push_time', 'arrival_time'),
        ),
        migrations.RenameIndex(
            model_name='submission',
            new_name='queue_submi_lms_cal_367510_idx',
            old_fields=('lms_callback_url', 'retired'),
        ),
        migrations.RenameIndex(
            model_name='submission',
            new_name='queue_submi_queue_n_9fcfbd_idx',
            old_fields=('queue_name', 'retired', 'pull_time', 'arrival_time'),
        ),
    ]
