# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-12-28 18:49
from __future__ import unicode_literals

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('songs', '0015_auto_20161228_1835'),
    ]

    operations = [
        migrations.AddField(
            model_name='trackrequest',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4),
        ),
        migrations.AlterField(
            model_name='track',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4),
        ),
    ]