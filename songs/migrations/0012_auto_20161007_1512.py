# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-10-07 15:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracks', '0001_initial'),
        ('songs', '0011_songtracks'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='songtracks',
            name='song',
        ),
        migrations.RemoveField(
            model_name='songtracks',
            name='track',
        ),
        migrations.AddField(
            model_name='song',
            name='tracks',
            field=models.ManyToManyField(to='tracks.Track'),
        ),
        migrations.DeleteModel(
            name='SongTracks',
        ),
    ]
