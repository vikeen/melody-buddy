# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-12-28 19:12
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('songs', '0016_auto_20161228_1849'),
    ]

    operations = [
        migrations.CreateModel(
            name='Stats',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('likes', models.IntegerField(default=0)),
                ('views', models.IntegerField(default=0)),
            ],
        ),
        migrations.RemoveField(
            model_name='song',
            name='likes',
        ),
        migrations.RemoveField(
            model_name='song',
            name='views',
        ),
        migrations.RemoveField(
            model_name='track',
            name='likes',
        ),
        migrations.AddField(
            model_name='stats',
            name='song',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='songs.Song'),
        ),
    ]