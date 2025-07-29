# Generated migration for trigram search indexes

from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fighters', '0007_update_method_choices'),
    ]

    operations = [
        # Ensure trigram extension is available (idempotent)
        TrigramExtension(),
        
        # Add GIN trigram indexes for fuzzy name matching
        migrations.RunSQL(
            # Create trigram indexes for optimized similarity search
            sql=[
                # Individual name fields for targeted search
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fighters_first_name_trgm ON fighters_fighter USING GIN (first_name gin_trgm_ops);",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fighters_last_name_trgm ON fighters_fighter USING GIN (last_name gin_trgm_ops);",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fighters_nickname_trgm ON fighters_fighter USING GIN (nickname gin_trgm_ops);",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fighters_display_name_trgm ON fighters_fighter USING GIN (display_name gin_trgm_ops);",
                
                # Combined index for full name search
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fighters_full_name_trgm ON fighters_fighter USING GIN ((first_name || ' ' || COALESCE(last_name, '')) gin_trgm_ops);",
                
                # Composite index for multi-field fuzzy search
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fighters_all_names_trgm ON fighters_fighter USING GIN ((first_name || ' ' || COALESCE(last_name, '') || ' ' || COALESCE(nickname, '') || ' ' || COALESCE(display_name, '')) gin_trgm_ops);",
            ],
            reverse_sql=[
                # Drop indexes if migration is reversed
                "DROP INDEX CONCURRENTLY IF EXISTS idx_fighters_first_name_trgm;",
                "DROP INDEX CONCURRENTLY IF EXISTS idx_fighters_last_name_trgm;",
                "DROP INDEX CONCURRENTLY IF EXISTS idx_fighters_nickname_trgm;",
                "DROP INDEX CONCURRENTLY IF EXISTS idx_fighters_display_name_trgm;",
                "DROP INDEX CONCURRENTLY IF EXISTS idx_fighters_full_name_trgm;",
                "DROP INDEX CONCURRENTLY IF EXISTS idx_fighters_all_names_trgm;",
            ]
        ),
        
        # Add trigram indexes for name variations
        migrations.RunSQL(
            sql=[
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fighter_name_variations_trgm ON fighters_fighternamevariation USING GIN (full_name_variation gin_trgm_ops);",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fighter_variations_first_trgm ON fighters_fighternamevariation USING GIN (first_name_variation gin_trgm_ops);",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fighter_variations_last_trgm ON fighters_fighternamevariation USING GIN (last_name_variation gin_trgm_ops);",
            ],
            reverse_sql=[
                "DROP INDEX CONCURRENTLY IF EXISTS idx_fighter_name_variations_trgm;",
                "DROP INDEX CONCURRENTLY IF EXISTS idx_fighter_variations_first_trgm;",
                "DROP INDEX CONCURRENTLY IF EXISTS idx_fighter_variations_last_trgm;",
            ]
        ),
    ]