# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-10-27 02:41
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('songs', '0003_auto_20161027_0121'),
    ]

    operations = [
        migrations.RenameField(
            model_name='trackrequest',
            old_name='media_name',
            new_name='audio_name',
        ),
        migrations.RenameField(
            model_name='trackrequest',
            old_name='media_url',
            new_name='audio_url',
        ),
    ]
