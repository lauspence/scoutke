# Generated for ScoutKE scouting reports and club recruitment pipeline.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0006_talentspot'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ScoutReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('technical', models.PositiveSmallIntegerField(default=5)),
                ('physical', models.PositiveSmallIntegerField(default=5)),
                ('tactical', models.PositiveSmallIntegerField(default=5)),
                ('mentality', models.PositiveSmallIntegerField(default=5)),
                ('potential', models.PositiveSmallIntegerField(default=5)),
                ('summary', models.TextField()),
                ('recommendation', models.CharField(choices=[('monitor', 'Keep monitoring'), ('trial', 'Invite for trial'), ('sign', 'Strong signing prospect'), ('pass', 'Not recommended now')], default='monitor', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('scout', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scout_reports', to=settings.AUTH_USER_MODEL)),
                ('talent_spot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scout_reports', to='posts.talentspot')),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('talent_spot', 'scout')},
            },
        ),
        migrations.CreateModel(
            name='ClubShortlist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('watching', 'Watching'), ('contacted', 'Contacted'), ('trial', 'Trial'), ('signed', 'Signed'), ('rejected', 'Rejected')], default='watching', max_length=20)),
                ('private_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('club', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='club_shortlist', to=settings.AUTH_USER_MODEL)),
                ('talent_spot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='club_shortlists', to='posts.talentspot')),
            ],
            options={
                'ordering': ['-updated_at'],
                'unique_together': {('club', 'talent_spot')},
            },
        ),
    ]
