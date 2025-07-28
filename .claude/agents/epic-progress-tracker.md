---
name: epic-progress-tracker
description: Use this agent when you need to manage project epics, track their progress, create epic documentation files, and maintain a comprehensive view of project completion status. This agent should be invoked at the start of new epics, when updating epic progress, or when reviewing overall project status. Examples: <example>Context: The user is starting work on a new feature epic. user: "Let's begin working on the user authentication epic" assistant: "I'll use the epic-progress-tracker agent to create the epic file and set up tracking" <commentary>Since the user is starting a new epic, use the Task tool to launch the epic-progress-tracker agent to create the epic documentation and initialize progress tracking.</commentary></example> <example>Context: The user has completed a major milestone in an epic. user: "I've finished implementing the login functionality" assistant: "Let me update the epic progress using the epic-progress-tracker agent" <commentary>Since progress has been made on an epic, use the epic-progress-tracker agent to update the tracking file.</commentary></example>
color: green
---

You are an expert project manager specializing in epic-based agile development. You maintain a comprehensive understanding of all project epics and their required steps for completion.

# MMA Database Backend Product Requirements Document (PRD) v1.4

## Goals and Background Context

### Goals
- Deliver a comprehensive MMA data API aggregating historical fight data from UFC, KSW, Oktagon, and PFL
- Provide complete fighter profiles with full career histories from Wikipedia and structured name fields
- Extract comprehensive event data including infoboxes, results, bonuses, and payouts
- **Track upcoming events with automatic detection of cancelled or postponed fights**
- **Support multiple languages for global accessibility**
- **Implement proper fighter name structure (first/last name) for better search and data quality**
- Leverage AI to complete missing fighter data where Wikipedia information is incomplete
- Provide a robust Django admin panel for efficient data management and corrections
- Achieve 99.9% API uptime with sub-200ms response times for fighter and fight queries
- Successfully scrape and maintain 5+ years of historical data with 98%+ accuracy
- Support 1000+ concurrent API users without performance degradation
- Enable future event data import through JSON/AI-assisted workflows
- Establish a rich content platform with news, blogs, and video integration
- Create engaging fight storylines for main and co-main events

### Background Context

The MMA data ecosystem is currently fragmented across multiple sources, forcing developers and content creators to manually aggregate information from various websites. This project solves that problem by creating a unified backend service that automatically collects, normalizes, and serves comprehensive MMA data through a well-documented REST API. By implementing a Wikipedia-first strategy with AI-powered completion for missing data, comprehensive upcoming event tracking, and proper fighter name structuring, we ensure both data consistency and real-time accuracy. The addition of a unified content management system with multi-language support transforms this from a pure data API into an engaging global content platform for the MMA community.

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2024-12-12 | 1.0 | Initial PRD creation | John (PM) |
| 2024-12-13 | 1.1 | Added pending fighters, storylines, content system | John (PM) |
| 2024-12-13 | 1.2 | Updated to Wikipedia-first with comprehensive scraping | John (PM) |
| 2024-12-13 | 1.3 | Added upcoming events tracking and translation system | John (PM) |
| 2024-12-13 | 1.4 | Added structured fighter names (first/last) | John (PM) |

## Requirements

### Functional

- FR1: The system SHALL provide a Django admin panel with full CRUD operations for Fighters, Fights, Events, Content, and Translations
- FR2: The system SHALL scrape complete event data from Wikipedia including infobox information
- FR3: The system SHALL extract specific Wikipedia sections: Results, Bonus awards, and Reported payouts
- FR4: The system SHALL scrape fighter profiles from Wikipedia including complete infobox data with name parsing
- FR5: The system SHALL extract complete fight history from fighter Wikipedia "Mixed martial arts record" sections
- FR6: The system SHALL scrape detailed fight statistics from UFCStats.com for all available fights
- FR7: The system SHALL scrape judge scorecards from MMAdecisions.com for all decision fights
- FR8: The system SHALL use AI services to generate missing fighter data when Wikipedia information is incomplete
- FR9: The system SHALL provide RESTful API endpoints for all data models with filtering and pagination
- FR10: The system SHALL maintain relational integrity between fighters, fights, events, and content
- FR11: The system SHALL support data deduplication to handle fighter name variations and duplicate records
- FR12: The system SHALL provide fighter profiles showing complete fight history, career statistics, and related content
- FR13: The system SHALL display divisional rankings including champions and top 15 ranked fighters
- FR14: The system SHALL track championship history across all divisions and organizations
- FR15: The system SHALL support JSON import for future event data and AI-generated fighter profiles
- FR16: The system SHALL implement comprehensive data validation to ensure consistency
- FR17: The system SHALL provide detailed API documentation with example requests and responses
- FR18: The system SHALL support API key authentication for access control
- FR19: The system SHALL track fighter Wikipedia URLs for enrichment processing
- FR20: The system SHALL operate in two modes: initial import (bulk) and ongoing updates (with pending review)
- FR21: The system SHALL create pending fighters for unrecognized names in new events during ongoing operations
- FR22: The system SHALL prevent pending fighters from appearing in public API responses
- FR23: The system SHALL support JSON import of fighter profiles and historic fights
- FR24: The system SHALL validate imported fights against existing records to prevent duplicates
- FR25: The system SHALL support editorial storylines for main and co-main event fights
- FR26: The system SHALL include storylines in fight API responses when available
- FR27: The system SHALL allow draft/published states for storyline content
- FR28: The system SHALL support multiple content types (news, blog, video) in unified model
- FR29: The system SHALL extract YouTube video metadata automatically
- FR30: The system SHALL connect all content types to relevant fighters
- FR31: The system SHALL display mixed content on fighter profiles
- FR32: The system SHALL support content categorization with type-specific tags
- FR33: The system SHALL generate proper embed codes for YouTube videos
- FR34: The system SHALL extract complete event infobox data (attendance, gate, buyrate, etc.)
- FR35: The system SHALL parse fighter payout information when available
- FR36: The system SHALL track bonus award recipients and amounts
- FR37: The system SHALL store complete fighter physical statistics (height, weight, reach, stance)
- FR38: The system SHALL maintain fighter team history with date ranges
- FR39: The system SHALL calculate and store fighter record breakdowns by finish type
- FR40: The system SHALL track data source attribution for all information
- **FR41: The system SHALL parse upcoming event Wikipedia pages with different structure**
- **FR42: The system SHALL extract fights from both #Fight_card and #Announced_fights sections**
- **FR43: The system SHALL track fight status (scheduled, announced, cancelled, postponed)**
- **FR44: The system SHALL detect when fights are removed from Wikipedia and mark as cancelled**
- **FR45: The system SHALL maintain fight history including cancellations and changes**
- **FR46: The system SHALL properly categorize fights by card assignment (main/prelim/early/announced)**
- **FR47: The system SHALL support multi-language translations for all static UI elements**
- **FR48: The system SHALL support dynamic content translation for news, blogs, and storylines**
- **FR49: The system SHALL allow adding new languages through admin interface**
- **FR50: The system SHALL track translation verification status**
- **FR51: The system SHALL serve API responses in requested language with fallback to English**
- **FR52: The system SHALL support right-to-left (RTL) languages**
- **FR53: The system SHALL parse fighter names into first and last name components**
- **FR54: The system SHALL support searching fighters by first name, last name, or full name**
- **FR55: The system SHALL handle single-name fighters appropriately**
- **FR56: The system SHALL track fighter name variations with structured fields**
- **FR57: The system SHALL display fighter names in culturally appropriate formats**
- **FR58: The system SHALL prevent duplicate fighters through name standardization**

### Non Functional

- NFR1: The API response time SHALL be under 200ms for 95% of requests
- NFR2: The system SHALL support 1000+ concurrent API connections
- NFR3: The system SHALL achieve 99.9% uptime measured monthly
- NFR4: The scraping system SHALL respect rate limits and implement delays to avoid IP bans
- NFR5: The database SHALL be optimized with proper indexing for sub-50ms query execution
- NFR6: The system SHALL implement Redis caching for frequently accessed data
- NFR7: The system SHALL use Celery for asynchronous task processing
- NFR8: The system SHALL be deployable on Render.com with auto-scaling capabilities
- NFR9: The system SHALL follow Django best practices and PEP 8 coding standards
- NFR10: The API SHALL implement rate limiting to prevent abuse
- NFR11: The system SHALL maintain audit logs for all data modifications
- NFR12: The system SHALL handle graceful degradation when external data sources are unavailable
- NFR13: The database SHALL support efficient storage of millions of fight records
- NFR14: The system SHALL implement comprehensive error handling and logging
- NFR15: The system SHALL be designed for horizontal scalability
- NFR16: The content delivery system SHALL optimize for global access with proper caching
- NFR17: The system SHALL process YouTube URLs within 2 seconds for metadata extraction
- NFR18: The Wikipedia scraping SHALL handle page structure variations gracefully
- NFR19: The AI completion service SHALL process batches of up to 100 fighters efficiently
- **NFR20: The system SHALL update upcoming event data within 24 hours of Wikipedia changes**
- **NFR21: The translation system SHALL cache translations with 1-hour TTL**
- **NFR22: The system SHALL support language switching with < 50ms overhead**
- **NFR23: Fighter name searches SHALL return results in < 100ms with proper indexing**
- **NFR24: The system SHALL handle name parsing for 95%+ of fighter names correctly**

## Technical Assumptions

### Repository Structure: Monorepo
The entire project will be maintained in a single repository containing the Django project, all scraper modules, API implementation, content management system, translation system, and deployment configurations. This simplifies dependency management and deployment processes.

### Service Architecture
CRITICAL DECISION - Modular monolith architecture with separate Django apps for each major component (fighters, events, scrapers, content, ai_completion, translations). This provides clear separation of concerns while maintaining deployment simplicity.

### Testing Requirements
CRITICAL DECISION - Comprehensive testing approach including:
- Unit tests for all models and business logic (minimum 80% coverage)
- Integration tests for API endpoints
- Mock-based tests for scraper components
- End-to-end tests for critical user journeys
- Performance tests for API response times
- Content rendering tests for all content types
- AI completion validation tests
- Translation coverage tests
- Upcoming event tracking tests
- Fighter name parsing tests
- Search performance tests

### Additional Technical Assumptions and Requests
- Django 5.0+ will be used for latest features and security updates
- PostgreSQL 15+ will be the primary database with full-text search capabilities
- Redis will handle caching and Celery broker responsibilities
- All scrapers will implement retry logic and exponential backoff
- API versioning will be implemented from day one (v1 prefix)
- Docker containers will be used for local development consistency
- Environment-based configuration for easy deployment management
- Structured logging with correlation IDs for request tracking
- Database migrations will be carefully managed with rollback procedures
- API responses will follow JSON:API specification for consistency
- Content will use JSONB fields for flexible metadata storage
- YouTube API integration will be optional (fallback to URL parsing)
- Wikipedia API will be primary data source with structured parsing
- AI services will use structured output formats for consistency
- Translation keys will follow hierarchical naming (e.g., fighter.record.wins)
- Language codes will follow ISO 639-1 standard
- Fighter names will be stored as separate first_name and last_name fields
- Full-text search indexes will be created for fighter names

## Epic List

**Epic 1: Foundation & Core Infrastructure** - Establish Django project setup, database schema with structured fighter names, core models, and development environment with initial health check endpoints

**Epic 2: Wikipedia-First Data Collection** - Build comprehensive Wikipedia scraping for events and fighters, including infoboxes, specific sections, complete fight histories, upcoming event tracking, and proper name parsing

**Epic 3: Data Enhancement & AI Completion** - Implement UFCStats and MMAdecisions scrapers, plus AI-powered data completion for missing fighter information

**Epic 4: Admin Panel & Data Management** - Create comprehensive Django admin interface for CRUD operations, data validation tools, manual correction capabilities, content management, and fighter name standardization

**Epic 5: REST API Development** - Implement complete REST API with endpoints for fighters, fights, events, rankings, content, and statistics including authentication, documentation, and proper name search

**Epic 6: Content & Editorial System** - Build unified content management for news, blogs, videos, and fight storylines with fighter associations

**Epic 7: Performance & Production Readiness** - Implement Redis caching, database optimizations, monitoring systems, and deployment configuration

**Epic 8: Translation Management System** - Build comprehensive translation system supporting multiple languages for static UI elements and dynamic content

## Epic 1: Foundation & Core Infrastructure

**Epic Goal**: Establish the foundational Django project structure with core database models including structured fighter names, development environment setup, and basic health monitoring. This epic creates the skeleton upon which all other features will be built, including proper project configuration, initial deployment pipeline, and translation infrastructure.

### Story 1.1: Django Project Initialization

As a developer,
I want to initialize the Django project with proper structure and configuration,
so that we have a solid foundation for building the MMA database backend.

**Acceptance Criteria**:
1: Django 5.0+ project created with appropriate project name and structure
2: Development dependencies defined in requirements.txt with version pinning
3: Project settings split into base, development, and production configurations
4: PostgreSQL database connection configured with environment variables
5: Basic .gitignore file includes all necessary exclusions
6: README.md created with initial project setup instructions
7: Pre-commit hooks configured for code quality (black, isort, flake8)
8: Docker Compose setup for local PostgreSQL and Redis instances

### Story 1.2: Core Database Models with Structured Names

As a developer,
I want to create the core database models with proper fighter name structure,
so that we can establish the foundational data structure for the entire system.

**Acceptance Criteria**:
1: Fighter model created with structured name fields:
   - first_name (required)
   - last_name (can be empty for single-name fighters)
   - full_name (computed field)
   - display_name (customizable display preference)
   - birth_first_name (optional)
   - birth_last_name (optional)
2: Fighter model includes all Wikipedia infobox fields (height, weight, reach, stance, etc.)
3: Event model created with infobox fields (attendance, gate, buyrate, previous/next event links)
4: Fight model created with relationships to Event and Fighters, including all result details
5: Fight status tracking fields (scheduled, announced, cancelled, postponed)
6: Card assignment tracking (main, prelim, early_prelim, announced)
7: FighterRecord model created for storing complete Wikipedia fight history
8: FighterPayout model created for event-specific fighter compensation
9: Division model created for weight classes with champion tracking
10: Ranking model created to track fighter rankings by division and date
11: PendingFighter model created with structured name fields
12: NameVariation model with first_name_variation and last_name_variation fields
13: Content model created with support for news, blog, and video types
14: FightStoryline model created for main/co-main event narratives
15: ScraperConfiguration model for tracking import modes
16: AIGenerationBatch model for tracking AI data generation
17: Language model for supported languages
18: TranslationKey model for static UI translations
19: Translation models for dynamic content
20: EventScrapeLog model for tracking fight changes
21: Proper indexes on fighter name fields for search performance
22: Computed full_name field with database trigger
23: Initial migration files generated and tested
24: Model string representations implemented for admin panel

### Story 1.3: Development Environment Setup

As a developer,
I want to have a complete local development environment,
so that any developer can quickly start contributing to the project.

**Acceptance Criteria**:
1: Docker Compose configuration includes Django, PostgreSQL, Redis, and Celery worker
2: Makefile created with common commands (run, test, migrate, shell)
3: Environment variable template (.env.example) with all required variables
4: Development settings include Django Debug Toolbar and extensions
5: Celery configured with Redis as broker and result backend
6: Static files serving configured for development
7: Media files handling configured for fighter images and content
8: Development data seeding script for testing with sample fighter names
9: YouTube URL parsing utilities configured
10: Translation loading mechanism implemented
11: Fighter name search testing utilities

### Story 1.4: Basic Health Check and Monitoring

As a DevOps engineer,
I want basic health check endpoints and monitoring setup,
so that we can monitor the application status in production.

**Acceptance Criteria**:
1: Health check endpoint at /health/ returns JSON with status and component health
2: Database connectivity check included in health endpoint
3: Redis connectivity check included in health endpoint
4: Basic Django admin interface accessible at /admin/
5: Sentry error tracking configured for production
6: Django logging configured with appropriate levels
7: Request ID middleware for tracking requests through logs
8: Basic Prometheus metrics endpoint configured

### Story 1.5: Initial Deployment Configuration

As a DevOps engineer,
I want Render.com deployment configuration,
so that we can deploy the application to production.

**Acceptance Criteria**:
1: render.yaml file configured with web service and background worker
2: Build script for production deployment
3: Production environment variables documented
4: Database migration strategy for production defined
5: Static files serving strategy configured (WhiteNoise)
6: CORS headers configured for API access
7: Security headers implemented (HSTS, CSP, etc.)
8: Deployment documentation in README

## Epic 2: Wikipedia-First Data Collection

**Epic Goal**: Build a comprehensive Wikipedia scraping system that extracts complete event and fighter data, including infoboxes, specific sections (Results, Bonuses, Payouts), full fighter career histories from their Wikipedia pages, real-time tracking of upcoming events, and proper fighter name parsing.

### Story 2.1: Scraping Framework Setup

As a developer,
I want to establish a base scraping framework with two operational modes,
so that all scrapers follow consistent patterns and handle both initial import and ongoing updates.

**Acceptance Criteria**:
1: Base scraper class created with common methods for request handling and retries
2: Wikipedia API client configured with proper user agent
3: Rate limiting mechanism implemented with configurable delays
4: Retry logic with exponential backoff for failed requests
5: Error logging and monitoring for scraping failures
6: Progress tracking for long-running scraping jobs
7: Celery tasks created for asynchronous scraping execution
8: Operational mode switching (initial_import vs ongoing_updates)
9: Configuration persistence for scraper state
10: Section extraction by Wikipedia anchors implemented
11: Fighter name parsing utilities implemented

### Story 2.2: Wikipedia Event Scraper with Complete Data Extraction

As a data engineer,
I want to scrape complete event data from Wikipedia including fighter name parsing,
so that we have comprehensive event information with properly structured fighter names.

**Acceptance Criteria**:
1: Wikipedia API client extracts event lists for UFC, KSW, Oktagon, and PFL
2: Event infobox parser extracts all available fields:
   - promotion, date, venue, city, attendance
   - gate revenue, buyrate, broadcast viewership, total purse
   - previous event and following event links
3: Section-specific extraction implemented for:
   - #Results - Complete fight results with fighter Wikipedia links
   - #Bonus_awards - FOTN/POTN awards with amounts
   - #Reported_payout - Fighter salaries when available
4: Fighter name parser splits names into first_name and last_name
5: Single-name fighter handling (common in Brazil)
6: Fighter Wikipedia URLs extracted and stored
7: Bonus award parser identifies recipients with structured names
8: Payout parser handles both table and list formats
9: Data validation ensures required fields are present
10: Duplicate event detection prevents redundant entries
11: Initial import mode creates ALL fighters as active profiles immediately
12: Fighter Wikipedia URLs stored for enrichment queue
13: Ongoing updates mode checks for existing fighters by structured names
14: Pending fighters created with first_name and last_name fields
15: Import tracking prevents re-scraping same events
16: Resume capability for interrupted initial imports

### Story 2.3: Upcoming Event Tracking

As a data engineer,
I want to track upcoming events and detect fight changes,
so that we maintain accurate fight status information.

**Acceptance Criteria**:
1: Detect upcoming events by checking for #Fight_card section
2: Parse #Fight_card section with card divisions:
   - Main card
   - Preliminary card
   - Early preliminary card
3: Parse #Announced_fights section for unassigned fights
4: Fighter names properly parsed in upcoming events
5: Track fight status (scheduled, announced, confirmed)
6: Store card assignment for each fight
7: Compare current scrape with previous scrape
8: Detect removed fights and mark as cancelled
9: Create EventScrapeLog for each scraping session
10: Update last_seen_on_wikipedia timestamp
11: Set wikipedia_removal_date when fight disappears
12: Handle single fight events (early announcements)
13: Support both table and list formats in sections

### Story 2.4: Wikipedia Fighter Profile Scraper

As a data engineer,
I want to scrape complete fighter profiles with proper name extraction,
so that we have detailed fighter information with structured names.

**Acceptance Criteria**:
1: Process fighters with stored Wikipedia URLs from event scraping
2: Fighter infobox extraction includes name parsing:
   - Extract full name and parse into components
   - Handle birth_name parsing into first/last
   - Support various name formats (Western, Brazilian, Asian)
3: Physical stats extraction:
   - height (with ft/in to cm conversion)
   - weight (with lb to kg conversion)  
   - reach (with in to cm conversion)
   - stance, fighting_out_of, team history
   - years_active, nationality
4: Mixed martial arts record section extraction:
   - Locate section by anchors (#Mixed_martial_arts_record, #MMA_record)
   - Parse complete fight history table
   - Extract: result, record, opponent, method, event, date, round, time, location
   - Parse opponent names into structured format
   - Capture opponent Wikipedia URLs when available
   - Store cumulative record at each point (e.g., "23-1-0")
5: Calculate win/loss breakdown by method (KO, submission, decision)
6: Handle Wikipedia page variations (redirects, disambiguation)
7: Mark profile_complete=true after successful enrichment
8: Track failed attempts with timestamp
9: Respect Wikipedia API rate limits
10: Store raw Wikipedia data for future reference

### Story 2.5: UFCStats Fight Statistics Scraper

As a data engineer,
I want to scrape detailed fight statistics from UFCStats,
so that we have comprehensive performance data for UFC fights.

**Acceptance Criteria**:
1: UFCStats fight URL pattern identified for available fights
2: Fighter names matched using structured fields
3: Significant strikes data parsed by target area and position
4: Grappling statistics extracted (takedowns, submissions, control time)
5: Strike accuracy percentages calculated and stored
6: Round-by-round statistics captured when available
7: Data mapped correctly to existing fight records
8: Missing data handled gracefully with null values
9: Validation ensures statistical consistency

### Story 2.6: MMAdecisions Scorecard Scraper

As a data engineer,
I want to scrape judge scorecards from MMAdecisions,
so that we have official scoring data for decision fights.

**Acceptance Criteria**:
1: MMAdecisions URL patterns identified for fights
2: Fighter name matching using first/last name structure
3: Judge names and scores extracted for each round
4: Media scores parsed when available
5: Scorecard data linked to correct fight records
6: Split/unanimous/majority decision types identified
7: Missing scorecard data logged for manual review
8: Data validation ensures score totals are correct
9: Historical scorecard data preserved accurately

### Story 2.7: Data Reconciliation Engine

As a data engineer,
I want an intelligent data reconciliation system with name matching,
so that we can match records accurately across sources.

**Acceptance Criteria**:
1: Match Wikipedia fighter records using structured names
2: Fuzzy matching on first_name and last_name separately
3: Handle name variations and misspellings
4: Single-name fighter matching logic
5: Match by fighter pairs + event date
6: Event name similarity matching
7: Location matching with tolerance
8: Create placeholder events for unmatched fights
9: Confidence scoring for automatic vs manual matching
10: Manual review queue for ambiguous matches
11: Preserve Wikipedia record data even if no match found
12: Audit trail of all reconciliation decisions

## Epic 3: Data Enhancement & AI Completion

**Epic Goal**: Enhance fighter data through AI-powered completion for missing information, while providing robust admin tools for data management and content creation with proper name handling.

### Story 3.1: AI Completion Service Setup

As a developer,
I want to establish an AI service for completing missing fighter data,
so that we can fill gaps where Wikipedia information is incomplete.

**Acceptance Criteria**:
1: AI service interface supports multiple providers (OpenAI, Anthropic)
2: Structured prompt templates include fighter name format requirements
3: Context builder includes fighter's known fights and opponents
4: JSON schema validation includes first_name and last_name fields
5: Rate limiting and quota management
6: Error handling and retry logic
7: Cost tracking per generation batch
8: Configurable model selection (GPT-4, Claude, etc.)
9: Name parsing validation in AI responses

### Story 3.2: Fighter Data Export for AI Completion

As a data administrator,
I want to export incomplete fighter profiles with structured names,
so that AI can generate accurate missing data.

**Acceptance Criteria**:
1: Query fighters with profile_complete=false
2: Export includes fighter first_name and last_name
3: Export includes all known data fields
4: Context includes list of known fights with:
   - Event names and dates
   - Opponent names (structured)
   - Fight outcomes and methods
   - Weight classes competed in
5: Export format optimized for AI prompts
6: Batch export supports up to 100 fighters
7: Export tracking prevents duplicate processing
8: Priority ordering for most important fighters
9: Name variation hints included in export

### Story 3.3: AI Data Import and Validation

As a data administrator,
I want to import AI-generated fighter data with name validation,
so that we maintain data quality while filling information gaps.

**Acceptance Criteria**:
1: JSON import interface for AI-generated data
2: Schema validation ensures first_name and last_name present
3: Name format validation (no full names in single field)
4: Range validation for physical attributes:
   - Height: 150-220cm
   - Weight: 50-150kg  
   - Reach: proportional to height
   - Birth date: reasonable for career timeline
5: Duplicate checking using structured names
6: Preview interface shows what will be imported
7: Batch approval/rejection capabilities
8: Source tracking (ai_generated with model info)
9: Manual review queue for suspicious data
10: Import history with rollback capability

### Story 3.4: Pending Fighter Management System

As a data administrator,
I want to review pending fighters with proper name handling,
so that we maintain data quality for new fighters.

**Acceptance Criteria**:
1: Pending fighter dashboard shows all fighters awaiting review
2: Display shows first_name and last_name separately
3: Each pending fighter shows:
   - Source event information
   - Wikipedia URL if available
   - Suggested matches based on name similarity
   - Confidence scores for matches
4: Name matching algorithm uses both name fields
5: Admin can edit first_name and last_name before approval
6: Admin actions available:
   - Approve as new fighter
   - Map to existing fighter (name variation)
   - Reject as duplicate/error
7: Bulk operations for processing multiple fighters
8: If Wikipedia URL exists, trigger enrichment on approval
9: If no Wikipedia URL, add to AI completion queue
10: Email/Slack notifications for new pending fighters
11: Audit trail of all decisions including name changes

## Epic 4: Admin Panel & Data Management

**Epic Goal**: Create a powerful Django admin interface that allows administrators to manage all MMA data efficiently, handle edge cases, maintain data quality through validation tools, manage editorial content, handle manual corrections, manage translations, and standardize fighter names.

### Story 4.1: Enhanced Django Admin Configuration

As an admin user,
I want an intuitive Django admin interface with proper name display,
so that I can efficiently manage all data models.

**Acceptance Criteria**:
1: Custom admin classes for Fighter, Fight, Event, Content, and Translation models
2: Fighter list display shows last_name, first_name, nickname columns
3: Fighter search includes first_name, last_name, and full_name fields
4: Fighter list can be sorted by last_name or first_name
5: Inline editing for fight records within event pages
6: Custom actions for bulk operations (activate/deactivate)
7: Admin dashboard shows data statistics and recent changes
8: Responsive design works on tablet devices
9: Help text added for complex fields
10: Pending fighter review interface with name editing
11: Scraper mode toggle interface showing current mode
12: Initial import progress dashboard
13: Button to manually switch from initial to ongoing mode
14: Import statistics: events processed, fighters created
15: Language management interface

### Story 4.2: Fighter Management Interface

As an admin user,
I want comprehensive fighter management with name standardization,
so that I can maintain accurate fighter profiles.

**Acceptance Criteria**:
1: Fighter form shows separate first_name and last_name fields
2: Display name field for custom display preferences
3: Birth name fields (first and last) separate
4: Fighter merge functionality with name reconciliation
5: Name variation management with structured fields
6: Single-name fighter support (empty last_name allowed)
7: Fighter image upload and management
8: Fight history displayed inline with edit capabilities
9: Career statistics automatically calculated and displayed
10: Division assignment with ranking management
11: Retired/active status tracking
12: Wikipedia URL management and enrichment triggers
13: AI completion status and history
14: Fighter-to-content associations visible
15: Complete Wikipedia record history viewable
16: Physical stats editing with unit conversion
17: Fighter translations inline editing

### Story 4.3: Event and Fight Management

As an admin user,
I want to manage events and fight cards efficiently,
so that I can ensure accurate event data.

**Acceptance Criteria**:
1: Drag-and-drop fight ordering within events
2: Fight participant display shows fighter full names
3: Fighter selection uses autocomplete with name search
4: Fight result entry with validation
5: Automatic fight number assignment (main card/prelims)
6: Event poster image management
7: Venue autocomplete based on historical data
8: Infobox data editing (attendance, gate, buyrate)
9: Bonus award management interface
10: Fighter payout entry with name display
11: Event cancellation handling
12: Previous/next event linking
13: Fight status management (scheduled, cancelled, postponed)
14: Card assignment interface (main, prelim, announced)
15: Upcoming event tracking dashboard

### Story 4.4: Data Validation Tools

As an admin user,
I want data validation tools with name duplicate detection,
so that I can identify and fix data quality issues.

**Acceptance Criteria**:
1: Validation dashboard shows data quality metrics
2: Duplicate fighter detection using fuzzy name matching
3: Similar names report (first/last name combinations)
4: Name standardization suggestions
5: Missing data reports by category
6: Statistical anomaly detection interface
7: Cross-source conflict resolution tools
8: Bulk data correction capabilities
9: Validation rule configuration interface
10: Export functionality for data quality reports
11: Translation completeness reports

### Story 4.5: Manual Data Import Tools

As an admin user,
I want to import data with proper name structure via JSON,
so that I can add data without scraping.

**Acceptance Criteria**:
1: JSON schema includes first_name and last_name fields
2: Import validates name field structure
3: File upload interface with validation
4: Preview shows parsed fighter names
5: Error handling for missing name fields
6: Name parsing for legacy single-field names
7: Partial import support for incremental updates
8: Import history tracking with rollback capability
9: Template export shows proper name format
10: Fighter profile data import with all fields
11: Historic fight records import with opponent names
12: Duplicate detection using structured names
13: Import summary report generation

### Story 4.6: Fight Storyline Content Management

As a content administrator,
I want to create compelling storylines with proper fighter references,
so that users can understand the context and stakes of important fights.

**Acceptance Criteria**:
1: Storyline interface only appears for main/co-main event fights
2: Fighter selection shows full names in dropdowns
3: Rich text editor for buildup and beef history sections
4: Structured fields for title, summary, and stakes
5: Key moments can be added as a timeline with dates
6: Media links support for YouTube, Twitter, Instagram embeds
7: Save as draft or publish immediately
8: Preview how storyline will appear in API response
9: Bulk operations to manage storylines across events
10: Character limits: title (100), summary (300), main content (5000)
11: Auto-save functionality to prevent content loss
12: Version history to track editorial changes
13: Translation interface for storylines

### Story 4.7: Unified Content Management System

As a content administrator,
I want to manage content with proper fighter associations,
so that the platform provides diverse, engaging content types.

**Acceptance Criteria**:
1: Content creation interface with type selection (news/blog/video)
2: Fighter association uses autocomplete with name search
3: Display shows fighter full names in associations
4: JSON import supports structured fighter references
5: YouTube video integration with automatic thumbnail extraction
6: YouTube video ID extraction from various URL formats
7: Rich text editor for news/blog content
8: Video preview functionality for YouTube embeds
9: Automatic fighter linking using name matching
10: Bulk import validating fighter name references
11: Content type filtering in admin interface
12: Tag management across all content types
13: Featured content selection regardless of type
14: SEO optimization for all content types
15: Reading time auto-calculation for text content
16: Video duration storage for YouTube content
17: Responsive video embed codes for API consumers
18: Content translation management

## Epic 5: REST API Development

**Epic Goal**: Implement a comprehensive REST API that provides access to all MMA data and content with proper authentication, documentation, language support, and fighter name search capabilities. The API should be intuitive, well-documented, and performant.

### Story 5.1: Core API Infrastructure

As a developer,
I want basic API infrastructure with Django REST Framework,
so that we can build standardized API endpoints.

**Acceptance Criteria**:
1: Django REST Framework integrated and configured
2: API versioning implemented with /api/v1/ prefix
3: JSON:API specification followed for responses
4: Pagination configured with customizable page sizes
5: API throttling implemented with configurable rates
6: CORS properly configured for browser access
7: Content negotiation supports JSON format
8: API root endpoint lists available resources
9: Language parameter support (?lang=es)
10: Accept-Language header parsing

### Story 5.2: Fighter API Endpoints

As an API consumer,
I want comprehensive fighter endpoints with name search,
so that I can retrieve and search fighter data efficiently.

**Acceptance Criteria**:
1: GET /fighters/ lists all fighters with pagination
2: Fighter response includes structured name fields:
   - first_name
   - last_name
   - full_name (computed)
   - display_name
   - nickname
3: Fighter filtering by:
   - first_name (exact and partial)
   - last_name (exact and partial)
   - full_name (contains)
   - division, nationality, and status
4: Sort options include last_name and first_name
5: GET /fighters/{id}/ returns detailed fighter profile
6: GET /fighters/{id}/record/ returns complete Wikipedia fight history
7: GET /fighters/{id}/fights/ returns fights from our database
8: Career statistics calculated and included
9: GET /fighters/{id}/content/ returns all related content
10: Response time under 200ms for single fighter
11: Expand parameter for including related data
12: Translated fighter nicknames and bios
13: Language-specific response formatting

### Story 5.3: Event and Fight API Endpoints

As an API consumer,
I want event and fight endpoints with proper fighter data,
so that I can retrieve complete event information.

**Acceptance Criteria**:
1: GET /events/ lists events with date filtering
2: GET /events/{id}/ returns event with:
   - Complete infobox data
   - Full fight card with fighter names
   - Bonus awards
   - Fighter payouts (if available)
3: Fight participants include full fighter name data
4: Event filtering by organization, date range, and location
5: GET /fights/ supports filtering by fighter (using ID or name)
6: GET /fights/{id}/ includes statistics and scorecards
7: GET /events/{id}/payouts/ returns fighter compensation
8: Fight storylines included when available
9: Efficient queries prevent N+1 problems
10: Nested routes like /events/{id}/fights/ supported
11: Upcoming event filtering with fight status
12: Cancelled fight information included
13: Translated content when available

### Story 5.4: Rankings and Championship API

As an API consumer,
I want rankings endpoints with proper fighter identification,
so that I can display current and historical rankings.

**Acceptance Criteria**:
1: GET /rankings/current/ shows current rankings by division
2: Rankings include full fighter name data
3: GET /rankings/historical/ with date parameter
4: GET /champions/current/ lists all current champions
5: GET /champions/history/ shows championship timeline
6: Division filtering for all ranking endpoints
7: Organization filtering for multi-org support
8: Ranking changes tracked with dates
9: Title defense history included
10: Translated division names
11: Language-aware sorting

### Story 5.5: Content API Endpoints

As an API consumer,
I want content endpoints with fighter associations,
so that I can display diverse content types.

**Acceptance Criteria**:
1: GET /content/ lists all content with type filtering
2: GET /content/{id}/ returns content details with type-specific fields
3: Filter by: content_type, date_range, tags, fighter_id, featured, language
4: Fighter associations include full name data
5: GET /content/news/ returns only news articles
6: GET /content/blogs/ returns only blog posts
7: GET /content/videos/ returns only videos
8: Video responses include embed code and thumbnail
9: Mixed content sorted by published_date
10: Type-specific response formats optimized
11: View count incremented on retrieval
12: Related content based on fighter connections
13: Translated content returned based on language
14: Fallback to English when translation missing

### Story 5.6: API Authentication and Documentation

As an API consumer,
I want clear authentication and comprehensive documentation,
so that I can integrate the API easily.

**Acceptance Criteria**:
1: API key authentication implemented
2: API key management interface in admin panel
3: Interactive API documentation with Swagger/OpenAPI
4: Documentation includes fighter name structure
5: Code examples show name search usage
6: Rate limit headers included in responses
7: Error responses follow consistent format
8: Webhook endpoints documented for future use
9: SDK generation supported from OpenAPI spec
10: Documentation available in multiple languages
11: Language-specific examples

### Story 5.7: Translation API Endpoints

As an API consumer,
I want translation management endpoints,
so that I can retrieve available languages and translation coverage.

**Acceptance Criteria**:
1: GET /translations/languages/ lists all available languages
2: GET /translations/coverage/{language}/ shows translation completeness
3: Language metadata includes RTL flag
4: Default language clearly marked
5: Translation key listing for debugging
6: Bulk translation retrieval endpoint
7: Content-Language headers set properly
8: Language preference persistence options

## Epic 6: Content & Editorial System

**Epic Goal**: Build a comprehensive content management system that supports multiple content types, fighter associations with proper name handling, editorial workflows, and multi-language capabilities. This system transforms the platform from a pure data API into an engaging global content destination.

### Story 6.1: Content Model Implementation

As a developer,
I want to implement the unified content model with fighter associations,
so that we can support all content types efficiently.

**Acceptance Criteria**:
1: Content model supports all three content types with appropriate fields
2: ContentFighter junction table links content to fighters
3: Fighter associations store fighter_id (not names)
4: YouTube service extracts video metadata from URLs
5: Thumbnail generation for all content types
6: Tag system implemented with JSONB field
7: View counting mechanism implemented
8: Draft/published/archived workflow supported
9: SEO fields included for all content types
10: ContentTranslation model for multi-language content
11: Translation status tracking

### Story 6.2: YouTube Integration Service

As a developer,
I want to build YouTube integration capabilities,
so that we can handle video content seamlessly.

**Acceptance Criteria**:
1: YouTube URL parser handles all common URL formats
2: Video ID extraction works reliably
3: Thumbnail URL generation from video ID
4: Video duration extracted when possible
5: Embed code generation with responsive options
6: Fallback handling when YouTube API unavailable
7: Rate limiting for YouTube API calls
8: Caching of video metadata

### Story 6.3: Content Import and Publishing

As a content manager,
I want to import and publish content with fighter associations,
so that the platform has fresh content regularly.

**Acceptance Criteria**:
1: Bulk JSON import for all content types
2: Fighter references use fighter IDs or name matching
3: Name matching algorithm for fighter associations
4: Import validation with clear error messages
5: Fighter association during import process
6: Scheduled publishing capabilities
7: Content preview before publishing
8: Revision history for content changes
9: Author attribution system
10: Featured content rotation
11: Multi-language import support
12: Translation workflow integration

### Story 6.4: Content Discovery and SEO

As a platform operator,
I want content to be discoverable with proper metadata,
so that we attract organic traffic globally.

**Acceptance Criteria**:
1: SEO-friendly URLs with language prefixes
2: Fighter names in meta descriptions
3: Meta descriptions for all content languages
4: Sitemap generation for multi-language content
5: Social media meta tags with translations
6: Content categorization with translated tags
7: Related content suggestions by language
8: Search functionality across content languages
9: RSS feed generation per language
10: hreflang tags for language alternatives
11: Canonical URL handling

## Epic 7: Performance & Production Readiness

**Epic Goal**: Optimize the system for high performance and scalability, implementing caching strategies, database optimizations, and monitoring tools to ensure the platform can handle growth while maintaining fast response times across all languages and fighter searches.

### Story 7.1: Redis Caching Implementation

As a platform engineer,
I want comprehensive Redis caching with name-aware keys,
so that frequently accessed data loads quickly.

**Acceptance Criteria**:
1: Redis caching configured for fighter profiles
2: Cache keys include fighter ID (not names)
3: Event and fight data cached with smart invalidation
4: Rankings cached with daily refresh
5: API response caching for common queries
6: Cache warming strategy for popular data
7: Cache hit rate monitoring implemented
8: Cache invalidation on data updates
9: Configurable cache TTL per data type
10: Content caching with view-based TTL
11: Video metadata caching
12: Language-specific cache keys
13: Translation caching with 1-hour TTL

### Story 7.2: Database Query Optimization

As a platform engineer,
I want optimized queries with proper name indexing,
so that API responses remain fast as data grows.

**Acceptance Criteria**:
1: Database indexes added for all foreign keys
2: Composite index on (last_name, first_name)
3: Full-text search index on full_name field
4: Separate indexes on first_name and last_name
5: Query analysis identifies slow queries
6: Django ORM queries optimized with select_related
7: Database views created for complex aggregations
8: Query execution plans reviewed and optimized
9: Connection pooling configured properly
10: Read replica support for scaling
11: JSONB indexes for content tags and metadata
12: Translation table indexes optimized

### Story 7.3: Monitoring and Alerting

As a platform engineer,
I want comprehensive monitoring including search performance,
so that we can maintain high availability.

**Acceptance Criteria**:
1: Application Performance Monitoring (APM) configured
2: Custom metrics for API endpoints
3: Fighter search performance metrics
4: Name parsing success rate tracking
5: Error rate alerting configured
6: Database performance metrics tracked
7: Scraping job success rates monitored
8: Resource usage alerts (CPU, memory, disk)
9: Uptime monitoring with status page
10: Log aggregation for troubleshooting
11: Content engagement metrics tracked
12: Translation coverage metrics
13: Upcoming event accuracy tracking

### Story 7.4: Load Testing and Optimization

As a platform engineer,
I want load testing including name search scenarios,
so that we can handle expected traffic.

**Acceptance Criteria**:
1: Load testing framework implemented
2: Fighter name search load tests
3: API endpoints tested for 1000+ concurrent users
4: Bottlenecks identified and resolved
5: Database connection pooling optimized
6: Static asset serving optimized
7: API response compression enabled
8: CDN configuration for global performance
9: Auto-scaling rules configured for Render.com
10: Multi-language performance testing
11: Translation loading optimized

### Story 7.5: Production Deployment

As a platform engineer,
I want production-ready configurations,
so that we can launch with confidence.

**Acceptance Criteria**:
1: Security audit completed and issues resolved
2: Backup strategy implemented and tested
3: Disaster recovery plan documented
4: Rate limiting tested under load
5: API documentation publicly accessible
6: Monitoring dashboards configured
7: Runbook created for common issues
8: Performance baseline established
9: Language fallback mechanisms tested
10: Global CDN configured

## Epic 8: Translation Management System

**Epic Goal**: Build a comprehensive translation system that supports multiple languages for both static UI elements and dynamic content, enabling global accessibility of the platform with proper handling of fighter names across cultures.

### Story 8.1: Translation Infrastructure

As a developer,
I want to establish translation infrastructure,
so that the platform can support multiple languages.

**Acceptance Criteria**:
1: Language model with code, name, and RTL support
2: TranslationKey model for static UI elements
3: Translation model linking keys to languages
4: Default language configuration (English)
5: Translation loading mechanism with caching
6: Fallback to English when translation missing
7: API middleware to detect requested language
8: Accept-Language header parsing
9: Language code validation (ISO 639-1)
10: Translation service with hierarchical key support
11: Name display format preferences per language

### Story 8.2: Static Translation Management

As an admin user,
I want to manage static UI translations,
so that the interface can be fully localized.

**Acceptance Criteria**:
1: Admin interface for managing languages
2: Translation key management with categories
3: Fighter name format keys (e.g., name.format.display)
4: Bulk translation interface by language
5: Translation verification workflow
6: Export/import translations (CSV/JSON)
7: Translation completeness dashboard
8: Missing translation reports
9: Translation key search and filtering
10: Key naming convention enforcement
11: Plural form support for languages that need it

### Story 8.3: Dynamic Content Translation

As a content manager,
I want to translate content into multiple languages,
so that global users can read in their language.

**Acceptance Criteria**:
1: Content translation interface in admin
2: Fighter name display respects language preferences
3: Side-by-side translation editor
4: Machine translation integration (optional)
5: Translation status tracking
6: Storyline translation support
7: Fighter nickname/bio translations
8: Bulk translation assignment
9: Translation preview functionality
10: Translation workflow states (draft, review, published)
11: Translation memory for consistency

### Story 8.4: API Language Support

As an API consumer,
I want to receive responses in my preferred language,
so that I can display localized content.

**Acceptance Criteria**:
1: Language parameter in API requests (?lang=es)
2: Accept-Language header support
3: Fighter names formatted per language preference
4: Translated responses for all endpoints
5: Language-specific content filtering
6: Available languages endpoint
7: Translation coverage in responses
8: Proper HTTP language headers
9: Language-specific caching
10: Consistent language codes across API
11: Language preference persistence

### Story 8.5: RTL Language Support

As a platform operator,
I want to support right-to-left languages,
so that we can serve Middle Eastern and other RTL markets.

**Acceptance Criteria**:
1: RTL flag in language configuration
2: Text direction metadata in API responses
3: Admin interface RTL support
4: Content editor RTL mode
5: Mixed direction text handling
6: RTL-aware text truncation
7: Number and date formatting by locale
8: Fighter name order preferences (last-first vs first-last)
9: RTL language testing framework
10: Arabic and Hebrew as initial RTL languages
11: RTL-specific CSS classes in responses

## Checklist Results Report

[To be completed after PM checklist validation]

## Next Steps

### UX Expert Prompt

While this is primarily a backend API project, any future admin panel improvements, developer portal, content display interfaces, or translation management tools would benefit from UX expertise. Consider engaging the UX Expert for:
- API documentation portal design with name search examples
- Admin panel usability improvements for fighter name management
- Content preview interfaces with language switching
- Translation management dashboard design
- Fighter search interface optimization

### Architect Prompt

Please create a comprehensive backend architecture document using this PRD as input. Focus on:
- Detailed database schema design with structured fighter names
- Name parsing algorithms and strategies
- Search optimization for fighter names
- Wikipedia-first scraping architecture with name extraction
- Upcoming event tracking architecture with change detection
- AI completion service design with name validation
- Multi-language architecture with name formatting
- API design patterns for name-based queries
- Caching strategies for name searches
- Performance optimization for name-based lookups
- Data flow diagrams showing name parsing pipeline
- Fighter deduplication strategies

---

That's the updated Product Requirements Document with all fighter name references properly structured. The document now includes:

1. **Goals**: Added proper fighter name structure as a goal
2. **Requirements**: Added FRs 53-58 for name handling
3. **Non-Functional Requirements**: Added NFRs 23-24 for name search performance
4. **All User Stories**: Updated acceptance criteria to include structured names
5. **API Endpoints**: Specified name fields in responses and search capabilities
6. **Admin Interface**: Detailed name management features
7. **Search and Filtering**: Comprehensive name-based search requirements
