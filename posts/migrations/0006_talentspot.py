# Generated for ScoutKE community scouting leads.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('players', '0003_alter_playerprofile_position_and_more'),
        ('posts', '0005_post_category_location_prospect_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TalentSpot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prospect_name', models.CharField(max_length=150)),
                ('position', models.CharField(choices=[('unknown', 'Unknown'), ('Forward', 'Forward'), ('Midfielder', 'Midfielder'), ('Defender', 'Defender'), ('Goalkeeper', 'Goalkeeper')], default='unknown', max_length=50)),
                ('age_estimate', models.PositiveIntegerField(blank=True, null=True)),
                ('team_or_school', models.CharField(blank=True, max_length=150)),
                ('location', models.CharField(max_length=150)),
                ('event_name', models.CharField(blank=True, max_length=150)),
                ('notes', models.TextField()),
                ('evidence_image', models.ImageField(blank=True, null=True, upload_to='talent_spots/images/')),
                ('evidence_video', models.FileField(blank=True, null=True, upload_to='talent_spots/videos/')),
                ('status', models.CharField(choices=[('new', 'New lead'), ('community_confirmed', 'Community confirmed'), ('scout_verified', 'Scout verified'), ('linked', 'Linked to player'), ('archived', 'Archived')], default='new', max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('confirmations', models.ManyToManyField(blank=True, related_name='confirmed_talent_spots', to=settings.AUTH_USER_MODEL)),
                ('linked_player', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='talent_spots', to='players.playerprofile')),
                ('source_post', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='talent_spot', to='posts.post')),
                ('spotted_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='talent_spots', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
