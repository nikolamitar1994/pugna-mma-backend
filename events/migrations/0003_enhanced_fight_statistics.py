# Generated manually for enhanced fight statistics

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0001_initial'),
        ('fighters', '0007_update_method_choices'),
    ]

    operations = [
        # Create round-by-round statistics model
        migrations.CreateModel(
            name='RoundStatistics',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('round_number', models.PositiveIntegerField()),
                
                # Fighter 1 Striking Statistics (by target)
                ('fighter1_head_strikes_landed', models.PositiveIntegerField(default=0)),
                ('fighter1_head_strikes_attempted', models.PositiveIntegerField(default=0)),
                ('fighter1_body_strikes_landed', models.PositiveIntegerField(default=0)),
                ('fighter1_body_strikes_attempted', models.PositiveIntegerField(default=0)),
                ('fighter1_leg_strikes_landed', models.PositiveIntegerField(default=0)),
                ('fighter1_leg_strikes_attempted', models.PositiveIntegerField(default=0)),
                
                # Fighter 1 Striking by Position
                ('fighter1_distance_strikes_landed', models.PositiveIntegerField(default=0)),
                ('fighter1_distance_strikes_attempted', models.PositiveIntegerField(default=0)),
                ('fighter1_clinch_strikes_landed', models.PositiveIntegerField(default=0)),
                ('fighter1_clinch_strikes_attempted', models.PositiveIntegerField(default=0)),
                ('fighter1_ground_strikes_landed', models.PositiveIntegerField(default=0)),
                ('fighter1_ground_strikes_attempted', models.PositiveIntegerField(default=0)),
                
                # Fighter 1 Grappling
                ('fighter1_takedowns_landed', models.PositiveIntegerField(default=0)),
                ('fighter1_takedown_attempts', models.PositiveIntegerField(default=0)),
                ('fighter1_submission_attempts', models.PositiveIntegerField(default=0)),
                ('fighter1_reversals', models.PositiveIntegerField(default=0)),
                ('fighter1_control_time', models.PositiveIntegerField(default=0)),  # seconds
                
                # Fighter 1 Other Stats
                ('fighter1_knockdowns', models.PositiveIntegerField(default=0)),
                ('fighter1_total_strikes_landed', models.PositiveIntegerField(default=0)),
                ('fighter1_total_strikes_attempted', models.PositiveIntegerField(default=0)),
                
                # Fighter 2 - Same structure
                ('fighter2_head_strikes_landed', models.PositiveIntegerField(default=0)),
                ('fighter2_head_strikes_attempted', models.PositiveIntegerField(default=0)),
                ('fighter2_body_strikes_landed', models.PositiveIntegerField(default=0)),
                ('fighter2_body_strikes_attempted', models.PositiveIntegerField(default=0)),
                ('fighter2_leg_strikes_landed', models.PositiveIntegerField(default=0)),
                ('fighter2_leg_strikes_attempted', models.PositiveIntegerField(default=0)),
                
                ('fighter2_distance_strikes_landed', models.PositiveIntegerField(default=0)),
                ('fighter2_distance_strikes_attempted', models.PositiveIntegerField(default=0)),
                ('fighter2_clinch_strikes_landed', models.PositiveIntegerField(default=0)),
                ('fighter2_clinch_strikes_attempted', models.PositiveIntegerField(default=0)),
                ('fighter2_ground_strikes_landed', models.PositiveIntegerField(default=0)),
                ('fighter2_ground_strikes_attempted', models.PositiveIntegerField(default=0)),
                
                ('fighter2_takedowns_landed', models.PositiveIntegerField(default=0)),
                ('fighter2_takedown_attempts', models.PositiveIntegerField(default=0)),
                ('fighter2_submission_attempts', models.PositiveIntegerField(default=0)),
                ('fighter2_reversals', models.PositiveIntegerField(default=0)),
                ('fighter2_control_time', models.PositiveIntegerField(default=0)),
                
                ('fighter2_knockdowns', models.PositiveIntegerField(default=0)),
                ('fighter2_total_strikes_landed', models.PositiveIntegerField(default=0)),
                ('fighter2_total_strikes_attempted', models.PositiveIntegerField(default=0)),
                
                # Round metadata
                ('round_duration', models.PositiveIntegerField(default=300)),  # seconds, default 5 minutes
                ('round_notes', models.TextField(blank=True)),
                
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                
                # Foreign key to fight statistics
                ('fight_statistics', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='round_stats',
                    to='events.fightstatistics'
                )),
            ],
            options={
                'db_table': 'round_statistics',
                'verbose_name': 'Round Statistics',
                'verbose_name_plural': 'Round Statistics',
                'ordering': ['fight_statistics', 'round_number'],
                'unique_together': [['fight_statistics', 'round_number']],
            },
        ),
        
        # Enhanced scorecard with round-by-round details
        migrations.CreateModel(
            name='RoundScore',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('round_number', models.PositiveIntegerField()),
                ('fighter1_round_score', models.PositiveIntegerField()),  # Usually 10 or 9
                ('fighter2_round_score', models.PositiveIntegerField()),  # Usually 9 or 8
                
                # Detailed scoring criteria
                ('fighter1_effective_striking', models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)),
                ('fighter1_effective_grappling', models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)),
                ('fighter1_control', models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)),
                ('fighter1_aggression', models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)),
                
                ('fighter2_effective_striking', models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)),
                ('fighter2_effective_grappling', models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)),
                ('fighter2_control', models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)),
                ('fighter2_aggression', models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)),
                
                # Round notes and highlights
                ('round_notes', models.TextField(blank=True)),
                ('key_moments', models.JSONField(default=list, blank=True)),
                
                ('created_at', models.DateTimeField(auto_now_add=True)),
                
                # Foreign key to scorecard
                ('scorecard', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='round_details',
                    to='events.scorecard'
                )),
            ],
            options={
                'db_table': 'round_scores',
                'verbose_name': 'Round Score',
                'verbose_name_plural': 'Round Scores',
                'ordering': ['scorecard', 'round_number'],
                'unique_together': [['scorecard', 'round_number']],
            },
        ),
        
        # Media/Fan scorecards for controversial decisions
        migrations.CreateModel(
            name='MediaScorecard',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('media_outlet', models.CharField(max_length=100)),
                ('scorer_name', models.CharField(max_length=100)),
                ('fighter1_score', models.PositiveIntegerField()),
                ('fighter2_score', models.PositiveIntegerField()),
                ('round_scores', models.JSONField(help_text="Round-by-round scores as array")),
                ('scorecard_url', models.URLField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                
                ('fight', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='media_scorecards',
                    to='events.fight'
                )),
            ],
            options={
                'db_table': 'media_scorecards',
                'verbose_name': 'Media Scorecard',
                'verbose_name_plural': 'Media Scorecards',
            },
        ),
        
        # Add indexes for performance
        migrations.AddIndex(
            model_name='roundstatistics',
            index=models.Index(fields=['fight_statistics', 'round_number'], name='idx_round_stats_fight_round'),
        ),
        
        migrations.AddIndex(
            model_name='roundscore',
            index=models.Index(fields=['scorecard', 'round_number'], name='idx_round_score_card_round'),
        ),
        
        migrations.AddIndex(
            model_name='mediascorecard',
            index=models.Index(fields=['fight'], name='idx_media_scorecard_fight'),
        ),
    ]