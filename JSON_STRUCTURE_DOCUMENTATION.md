# Fighter JSON Structure Documentation

## Complete Fighter Profile JSON Format

This document outlines the exact JSON structure needed to populate a complete fighter profile including fight history in the MMA database.

## 📋 Main Structure

```json
{
  "entity_type": "fighter",           // REQUIRED: Must be "fighter"
  "template_version": "1.0",          // REQUIRED: Template version
  "generation_date": "2025-01-29T20:30:00Z",  // ISO datetime
  "fighter_data": { ... },            // REQUIRED: Core fighter information
  "fight_history": [ ... ],           // OPTIONAL: Array of fight records
  "calculated_statistics": { ... },   // OPTIONAL: Computed stats
  "import_settings": { ... },         // OPTIONAL: Import behavior
  "source_context": { ... }           // OPTIONAL: Source metadata
}
```

## 🧑 Fighter Data Structure

### Personal Information
```json
"personal_info": {
  "first_name": "string",             // REQUIRED: Fighter's first name
  "last_name": "string",              // REQUIRED: Fighter's last name  
  "display_name": "string",           // OPTIONAL: Custom display name
  "nickname": "string",               // OPTIONAL: Fighter nickname
  "birth_first_name": "string",       // OPTIONAL: Legal birth first name
  "birth_last_name": "string",        // OPTIONAL: Legal birth last name
  "date_of_birth": "YYYY-MM-DD",      // OPTIONAL: Birth date in ISO format
  "birth_place": "string",            // OPTIONAL: Place of birth
  "nationality": "string"             // OPTIONAL: Country/nationality
}
```

### Physical Attributes
```json
"physical_attributes": {
  "height_cm": 175,                   // OPTIONAL: Height in centimeters (120-250)
  "weight_kg": 70.0,                  // OPTIONAL: Weight in kilograms (40-200)  
  "reach_cm": 188,                    // OPTIONAL: Reach in centimeters (120-250)
  "stance": "orthodox"                // OPTIONAL: "orthodox", "southpaw", "switch"
}
```

### Career Information
```json
"career_info": {
  "fighting_out_of": "string",        // OPTIONAL: Location fighter represents
  "team": "string",                   // OPTIONAL: Fighting team/gym
  "years_active": "string",           // OPTIONAL: e.g., "2008-present"
  "is_active": true                   // OPTIONAL: Currently active fighter
}
```

### Media Links
```json
"media_links": {
  "profile_image_url": "string",      // OPTIONAL: Fighter photo URL
  "wikipedia_url": "string",          // OPTIONAL: Wikipedia page URL
  "social_media": {                   // OPTIONAL: Social media handles
    "instagram": "string",
    "twitter": "string", 
    "facebook": "string",
    "tiktok": "string"
  }
}
```

## 🥊 Fight History Structure

Each fight in the `fight_history` array follows this structure:

```json
{
  "fight_order": 28,                  // REQUIRED: Sequential fight number in career
  "result": "win",                    // REQUIRED: "win", "loss", "draw", "no_contest"
  "fighter_record_at_time": "22-6-0", // OPTIONAL: Record before this fight
  
  "opponent_info": {
    "opponent_first_name": "string",   // REQUIRED: Opponent's first name
    "opponent_last_name": "string",    // REQUIRED: Opponent's last name
    "opponent_full_name": "string",    // REQUIRED: Full opponent name
    "opponent_fighter_id": null        // OPTIONAL: UUID if opponent exists in DB
  },
  
  "fight_details": {
    "method": "TKO",                   // REQUIRED: "Decision", "KO", "TKO", "Submission"
    "method_description": "string",    // OPTIONAL: Detailed method description
    "ending_round": 1,                 // OPTIONAL: Round fight ended
    "ending_time": "5:00",             // OPTIONAL: Time fight ended (MM:SS)
    "scheduled_rounds": 5,             // OPTIONAL: Number of scheduled rounds
    "is_title_fight": false,           // OPTIONAL: Was this a title fight
    "is_interim_title": false,         // OPTIONAL: Was this for interim title
    "title_belt": "string"             // OPTIONAL: Title being contested
  },
  
  "event_info": {
    "event_name": "string",            // REQUIRED: Full event name
    "event_date": "2021-07-10",       // REQUIRED: Event date (YYYY-MM-DD)
    "organization_name": "string",     // REQUIRED: Organization (UFC, Bellator, etc.)
    "weight_class_name": "string",     // OPTIONAL: Weight class for this fight
    "location": "string",              // OPTIONAL: Full location string
    "venue": "string",                 // OPTIONAL: Venue name
    "city": "string",                  // OPTIONAL: City
    "state": "string",                 // OPTIONAL: State/Province
    "country": "string"                // OPTIONAL: Country
  },
  
  "additional_info": {
    "notes": "string",                 // OPTIONAL: Additional fight notes
    "performance_bonuses": ["array"],  // OPTIONAL: Performance bonuses received
    "data_source": "string",           // OPTIONAL: Source of this data
    "source_url": "string"            // OPTIONAL: URL of data source
  }
}
```

## 📊 Calculated Statistics (Optional)

```json
"calculated_statistics": {
  "career_record": {
    "total_fights": 28,
    "wins": 22,
    "losses": 6, 
    "draws": 0,
    "no_contests": 0
  },
  "win_breakdown": {
    "wins_by_ko": 10,
    "wins_by_tko": 8,
    "wins_by_submission": 1,
    "wins_by_decision": 3
  },
  "performance_metrics": {
    "finish_rate": 0.86,
    "current_streak": "string",
    "title_fights": 4,
    "title_wins": 2,
    "performance_bonuses": 12
  }
}
```

## ⚙️ Import Settings (Optional)

```json
"import_settings": {
  "update_existing": false,           // Update if fighter already exists
  "validate_opponents": true,         // Validate opponent names exist
  "create_missing_events": false,     // Create events if they don't exist
  "link_to_existing_fights": true,    // Link to existing Fight records
  "auto_calculate_stats": true        // Automatically calculate statistics
}
```

## 📝 Source Context (Optional)

```json
"source_context": {
  "import_source": "string",          // Source of this data
  "research_date": "2025-01-29",     // When data was researched
  "researcher": "string",             // Who researched the data
  "verification_level": "high",       // Data quality level
  "last_updated": "2025-01-29T20:30:00Z"  // Last update timestamp
}
```

## 🎯 Minimal Required JSON

The absolute minimum JSON to create a fighter:

```json
{
  "entity_type": "fighter",
  "template_version": "1.0",
  "fighter_data": {
    "personal_info": {
      "first_name": "John",
      "last_name": "Doe"
    }
  }
}
```

## 🎯 Recommended Complete JSON

For a high-quality fighter profile, include:

### Required Fields:
- `first_name`, `last_name`
- `entity_type`, `template_version`

### Highly Recommended:
- `nationality`, `date_of_birth` 
- `height_cm`, `weight_kg`, `stance`
- At least 3-5 most recent fights in `fight_history`

### Nice to Have:
- `reach_cm`, `fighting_out_of`, `team`
- `wikipedia_url`, `profile_image_url`
- Complete fight history
- Social media links

## 📋 Field Validation Rules

| Field | Type | Range/Format | Notes |
|-------|------|--------------|-------|
| `height_cm` | Integer | 120-250 | Centimeters |
| `weight_kg` | Decimal | 40.0-200.0 | Kilograms |
| `reach_cm` | Integer | 120-250 | Usually close to height |
| `date_of_birth` | String | YYYY-MM-DD | ISO date format |
| `stance` | String | orthodox, southpaw, switch | Exact values only |
| `result` | String | win, loss, draw, no_contest | Fight result |
| `method` | String | decision, ko, tko, submission | Fight ending method (lowercase) |

## 🚀 Usage Examples

### Import via Management Command:
```bash
python manage.py import_from_json --file fighter_profile.json
```

### Import via Django Admin:
1. Go to `/admin/fighters/fighter/import-json/`
2. Upload your JSON file
3. Review validation results
4. Confirm import

### Export Existing Fighter:
```bash
python manage.py export_templates --type fighter --ids FIGHTER_UUID --output fighter_export.json --pretty
```

## ⚠️ Important Notes

1. **UUIDs**: All `*_id` fields expect UUID format, not integers
2. **Dates**: All dates must be in YYYY-MM-DD format
3. **Validation**: The system validates all data before import
4. **Duplicates**: System checks for existing fighters by name
5. **Fight Linking**: Fights will be linked to existing Fight records if found
6. **Statistics**: Win/loss records are calculated automatically from fight history
7. **Data Quality**: Incomplete profiles get lower data quality scores

## 🔗 Related Files

- Full example: `FIGHTER_JSON_STRUCTURE.json`
- Import command: `manage.py import_from_json`
- Export command: `manage.py export_templates`
- Template generator: `manage.py generate_json_templates`