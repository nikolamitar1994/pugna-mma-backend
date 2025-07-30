# Enhanced Wikipedia UFC Scraper Usage Guide

## Overview

The enhanced Wikipedia UFC scraper is a production-ready Django management command that scrapes UFC events from Wikipedia and integrates them into your existing Django models with comprehensive fighter management.

## Key Features

- **Complete Event/Fight/Fighter Creation**: Automatically creates Event, Fight, FightParticipant, and Fighter records
- **Fighter Integration**: Intelligently matches existing fighters or creates new ones with Wikipedia URLs
- **Pending Fighter Workflow**: Optional review workflow for new fighters before creation
- **Interconnected Fight History**: Automatically creates FightHistory perspectives using your existing system
- **Rate Limiting**: Respects Wikipedia's API limits (1 request/second by default)
- **Comprehensive Error Handling**: Production-ready with retries and detailed logging
- **Name Variation Tracking**: Handles different name formats and creates variations
- **Wikipedia URL Extraction**: Captures fighter Wikipedia URLs when available

## Usage Examples

### Scrape a Single Event

```bash
# Scrape UFC 300
python manage.py scrape_ufc_wikipedia_enhanced --event-number 300

# Scrape specific event by name
python manage.py scrape_ufc_wikipedia_enhanced --event "UFC Fight Night: Silva vs Henderson"

# Scrape with verification
python manage.py scrape_ufc_wikipedia_enhanced --event-number 300 --verify-data --verbose
```

### Scrape Recent Events

```bash
# Scrape events from last 30 days
python manage.py scrape_ufc_wikipedia_enhanced --recent 30

# Scrape events from last 90 days with updates
python manage.py scrape_ufc_wikipedia_enhanced --recent 90 --update-existing
```

### Fighter Creation Options

```bash
# Automatically create Fighter records (default)
python manage.py scrape_ufc_wikipedia_enhanced --event-number 300 --create-fighters

# Use pending fighter workflow for manual review
python manage.py scrape_ufc_wikipedia_enhanced --event-number 300 --pending-only

# Don't create any new fighters (existing fighters only)
python manage.py scrape_ufc_wikipedia_enhanced --event-number 300 --no-create-fighters
```

### Performance and Rate Limiting

```bash
# Adjust rate limiting (default 1.0 seconds between requests)
python manage.py scrape_ufc_wikipedia_enhanced --event-number 300 --rate-limit 2.0

# Process in smaller batches
python manage.py scrape_ufc_wikipedia_enhanced --recent 30 --batch-size 3

# Increase retry attempts
python manage.py scrape_ufc_wikipedia_enhanced --event-number 300 --max-retries 5
```

### Dry Run and Testing

```bash
# See what would be scraped without making changes
python manage.py scrape_ufc_wikipedia_enhanced --event-number 300 --dry-run

# Verbose output for debugging
python manage.py scrape_ufc_wikipedia_enhanced --event-number 300 --verbose

# Quiet mode (errors only)
python manage.py scrape_ufc_wikipedia_enhanced --event-number 300 --quiet
```

## Command Options Reference

### Scraping Targets
- `--event TEXT`: Scrape specific event by name or Wikipedia URL
- `--event-number INT`: Scrape UFC event by number (e.g., 300)
- `--recent INT`: Scrape events from last N days
- `--date-range START END`: Scrape events in date range (YYYY-MM-DD format)
- `--all-events`: Scrape all UFC events (use with extreme caution)

### Fighter Processing
- `--create-fighters`: Automatically create Fighter records (default: True)
- `--pending-only`: Create PendingFighter records for manual review
- `--update-existing`: Update existing events and fighters

### Performance
- `--rate-limit FLOAT`: Seconds between Wikipedia requests (default: 1.0)
- `--batch-size INT`: Events per database transaction (default: 5)
- `--max-retries INT`: Maximum retry attempts (default: 3)

### Output & Debugging
- `--dry-run`: Show what would be scraped without changes
- `--verbose`: Enable detailed logging
- `--quiet`: Suppress output except errors
- `--progress`: Show progress indicators (default: True)
- `--verify-data`: Verify scraped data completeness

## Integration with Existing Models

### Fighter Integration
The scraper integrates seamlessly with your existing Fighter model:

1. **Existing Fighter Detection**: Uses multiple strategies to find existing fighters:
   - Exact name matching (first_name + last_name)
   - Display name matching
   - Nickname matching
   - Name variation matching
   - Fuzzy matching with similarity scoring
   - Integration with your existing FighterMatcher service

2. **New Fighter Creation**: Creates Fighter records with:
   - Structured names (first_name, last_name)
   - Wikipedia URLs when available
   - Proper data_source attribution
   - Integration with your data quality scoring

3. **Name Variations**: Automatically creates FighterNameVariation records for:
   - Different name formats found in Wikipedia
   - Nickname variations
   - Alternative spellings

### Event and Fight Integration
- Creates complete Event records with Wikipedia metadata
- Links to existing UFC Organization record
- Creates Fight records with proper ordering and status
- Creates FightParticipant records for fighter-fight relationships
- Automatically generates FightHistory perspectives using your interconnected system

### Pending Fighter Workflow
When using `--pending-only`:
- Creates PendingFighter records instead of Fighter records
- Runs automatic duplicate detection
- Provides confidence scoring for admin review
- Stores structured data for easy approval process

## Expected Output

```
==================================================
SCRAPING STATISTICS
==================================================
Events processed: 1
Events created: 1
Events updated: 0
Events skipped: 0
Fights created: 13
Fighters found: 18
Fighters created: 8
Pending fighters created: 0
Fighters updated: 3
Wikipedia URLs added: 11
Name variations added: 2
```

## Error Handling

The scraper includes comprehensive error handling:

- **Network Errors**: Automatic retries with exponential backoff
- **Wikipedia API Errors**: Rate limiting and 429 response handling
- **Parsing Errors**: Graceful handling of malformed Wikipedia pages
- **Database Errors**: Transaction rollback on failures
- **Fighter Matching Errors**: Detailed logging of matching issues

## Best Practices

1. **Start Small**: Test with single events before batch processing
2. **Use Dry Run**: Always test with `--dry-run` first
3. **Monitor Rate Limits**: Keep default 1-second rate limit for Wikipedia
4. **Review Pending Fighters**: Use `--pending-only` for new data sources
5. **Enable Logging**: Use `--verbose` for debugging issues
6. **Verify Data**: Use `--verify-data` for quality assurance

## Troubleshooting

### Common Issues

1. **Fighter Not Found Errors**:
   ```bash
   # Use pending workflow to review
   python manage.py scrape_ufc_wikipedia_enhanced --event-number 300 --pending-only --verbose
   ```

2. **Wikipedia Page Not Found**:
   ```bash
   # Check event identifier format
   python manage.py scrape_ufc_wikipedia_enhanced --event "UFC_300" --dry-run
   ```

3. **Rate Limiting**:
   ```bash
   # Increase rate limit
   python manage.py scrape_ufc_wikipedia_enhanced --event-number 300 --rate-limit 2.0
   ```

### Debug Mode
```bash
# Maximum debugging information
python manage.py scrape_ufc_wikipedia_enhanced --event-number 300 --verbose --verify-data --dry-run
```

## Integration with Admin Panel

After scraping, you can:

1. **Review Pending Fighters**: Admin panel shows pending fighters with confidence scores
2. **Approve/Reject**: Bulk approve high-confidence pending fighters
3. **Review Fight History**: Check interconnected fight history was created correctly
4. **Verify Data Quality**: Use built-in data quality scoring
5. **Manage Name Variations**: Review and edit fighter name variations

## Development Notes

The scraper is built with modularity in mind:

- `WikipediaUFCEnhancedScraper`: Handles Wikipedia parsing
- `EnhancedFighterScrapingIntegration`: Manages fighter integration
- `Command`: Orchestrates the process with CLI interface

This allows for easy testing and modification of individual components while maintaining the overall workflow integrity.