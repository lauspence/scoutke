# Generated for ScoutKE social scouting posts.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0004_post_original_post'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='category',
            field=models.CharField(
                choices=[
                    ('general', 'Football talk'),
                    ('talent', 'Talent spotted'),
                    ('match', 'Match update'),
                    ('news', 'Local football news'),
                ],
                default='general',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='post',
            name='location',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='post',
            name='prospect_name',
            field=models.CharField(blank=True, max_length=150),
        ),
    ]
