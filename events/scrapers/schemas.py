"""
Pydantic schemas for UFC Wikipedia scraper structured output with Gemini AI
"""
from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel, Field


class FighterInfoSchema(BaseModel):
    """Fighter information extracted from Wikipedia fight cards"""
    first_name: str = Field(..., description="Fighter's first name")
    last_name: str = Field(default="", description="Fighter's last name (empty for single-name fighters)")
    nickname: Optional[str] = Field(default=None, description="Fighter's nickname without quotes")
    wikipedia_url: Optional[str] = Field(default=None, description="Full Wikipedia URL (convert relative URLs to absolute)")
    nationality: Optional[str] = Field(default=None, description="Fighter's nationality/country")
    result: str = Field(..., description="Fight result: 'win', 'loss', 'draw', or 'no_contest'")


class BonusAwardSchema(BaseModel):
    """Performance bonus awards"""
    award_type: str = Field(..., description="Type: 'Performance of the Night', 'Fight of the Night', 'Submission of the Night', 'Knockout of the Night'")
    fighter_name: str = Field(..., description="Full fighter name who received the award")
    amount: Optional[int] = Field(default=50000, description="Bonus amount in USD")


class FightResultSchema(BaseModel):
    """Individual fight result from Wikipedia results table"""
    fight_order: int = Field(..., description="Fight order on card (1 = main event, 2 = co-main, etc.)")
    fight_section: Optional[str] = Field(default=None, description="Fight section from Wikipedia (e.g., 'Main Card', 'Preliminaries', 'Quarter Finals', 'Final', 'Alternate Bout', 'Superfight Championship')")
    is_main_event: bool = Field(default=False, description="True if this is the main event")
    is_title_fight: bool = Field(default=False, description="True if this is a title fight")
    weight_class: str = Field(..., description="Weight class name (e.g., 'Lightweight', 'Heavyweight', 'Openweight'). Use 'Openweight' for N/A or no weight class")
    scheduled_rounds: int = Field(default=3, description="Scheduled number of rounds (3 or 5)")
    
    # Fighters
    fighter1: FighterInfoSchema = Field(..., description="First fighter (winner if there's a winner)")
    fighter2: FighterInfoSchema = Field(..., description="Second fighter")
    
    # Fight outcome
    winner_name: Optional[str] = Field(default=None, description="Full name of winning fighter")
    method: Optional[str] = Field(default=None, description="Finish method: KO, TKO, Submission, Decision, etc.")
    method_details: Optional[str] = Field(default=None, description="Specific details: submission type, punch type, etc.")
    ending_round: int = Field(default=1, description="Round the fight ended (defaults to 1 if not specified)")
    ending_time: Optional[str] = Field(default=None, description="Time in MM:SS format")
    referee: Optional[str] = Field(default=None, description="Referee name")
    
    # Additional context
    notes: Optional[str] = Field(default=None, description="Any additional notes about the fight")


class EventInfoSchema(BaseModel):
    """UFC event information extracted from Wikipedia"""
    name: str = Field(..., description="Official event name")
    name_variations: List[str] = Field(default_factory=list, description="Alternative names found on the page")
    event_number: Optional[int] = Field(default=None, description="UFC event number if numbered event")
    date: str = Field(..., description="Event date in YYYY-MM-DD format")
    
    # Location details
    location: str = Field(..., description="Full location string")
    venue: Optional[str] = Field(default=None, description="Venue name")
    city: Optional[str] = Field(default=None, description="City name")
    state: Optional[str] = Field(default=None, description="State/province")
    country: Optional[str] = Field(default=None, description="Country name")
    
    # Event metrics
    attendance: Optional[int] = Field(default=None, description="Total attendance number")
    gate_revenue: Optional[float] = Field(default=None, description="Gate revenue in USD")
    ppv_buys: Optional[int] = Field(default=None, description="Pay-per-view purchases")
    
    # URLs and media
    wikipedia_url: str = Field(..., description="Wikipedia URL of the event page")
    poster_url: Optional[str] = Field(default=None, description="Event poster image URL")
    
    # Broadcast information
    broadcast_info: Dict[str, Any] = Field(default_factory=dict, description="TV/streaming broadcast details")


class UFCEventSchema(BaseModel):
    """Complete UFC event data structure for Gemini AI structured output"""
    event: EventInfoSchema = Field(..., description="Event information")
    fights: List[FightResultSchema] = Field(..., description="List of all fights on the card")
    bonus_awards: List[BonusAwardSchema] = Field(default_factory=list, description="Performance bonuses awarded")
    
    # Processing metadata
    scraped_sections: Dict[str, bool] = Field(
        default_factory=lambda: {
            "infobox": False,
            "results_table": False,
            "bonus_awards": False,
            "first_paragraph": False
        },
        description="Which sections were successfully scraped"
    )
    processing_notes: List[str] = Field(default_factory=list, description="Any processing notes or warnings")


class ScrapingResultSchema(BaseModel):
    """Raw HTML sections extracted from Wikipedia before Gemini processing"""
    event_url: str = Field(..., description="Wikipedia URL that was scraped")
    event_title: str = Field(..., description="Page title from Wikipedia")
    
    # Raw HTML sections
    first_paragraph_html: Optional[str] = Field(default=None, description="First paragraph HTML")
    infobox_html: Optional[str] = Field(default=None, description="Infobox table HTML")
    results_table_html: Optional[str] = Field(default=None, description="Fight results table HTML")
    bonus_awards_html: Optional[str] = Field(default=None, description="Bonus awards section HTML")
    
    # Extraction metadata
    scraping_timestamp: str = Field(..., description="ISO timestamp when scraped")
    extraction_success: bool = Field(..., description="Whether scraping was successful")
    error_messages: List[str] = Field(default_factory=list, description="Any errors encountered")


# Gemini AI prompt templates
GEMINI_PROMPTS = {
    "event_extraction": """
You are an expert MMA data extraction specialist. Extract structured UFC event data from the provided Wikipedia HTML sections.

IMPORTANT INSTRUCTIONS:
1. Extract fighter Wikipedia URLs from href attributes in fighter name cells
2. Convert relative Wikipedia URLs (starting with /wiki/) to absolute URLs (https://en.wikipedia.org/wiki/...)
3. Determine fight order based on table position (main event = 1, co-main = 2, etc.)
4. Extract fighter nationality from flag images or country indicators
5. WEIGHT CLASS HANDLING:
   - If weight class shows "N/A" or is empty/missing, use "Openweight"
   - Early UFC events (UFC 1-20) often had no weight classes - all should be "Openweight"
6. ROUND HANDLING:
   - If round number is missing or not specified, default to 1
   - Early UFC events only had 1 round, so missing round = Round 1
7. FIGHT SECTION HANDLING:
   - Extract fight section headers from Wikipedia (e.g., "Main Card", "Preliminaries", "Quarter Finals", "Final")
   - Early UFC events had tournament brackets: "Opening Round", "Quarter Finals", "Semi Finals", "Final"
   - Some events had special sections: "Alternate Bout", "Superfight Championship"
   - Modern events: "Main Card", "Preliminaries", "Early Preliminaries"
   - Use the exact section name as it appears on Wikipedia
8. METHOD FORMATTING - VERY IMPORTANT:
   - Extract ONLY the base method (e.g., "KO", "TKO", "Submission", "Decision")
   - Put the specific details in method_details (e.g., "punches", "rear-naked choke", "unanimous")
   - NEVER include scorecards in method or method_details - ignore scorecards completely
   - Examples:
     * "KO (punches)" becomes: method="KO", method_details="punches"
     * "Decision (unanimous) (49-45, 49-45, 49-45)" becomes: method="Decision", method_details="unanimous"
     * "Submission (rear-naked choke)" becomes: method="Submission", method_details="rear-naked choke"
9. Parse bonus awards carefully - multiple fighters can receive same award type

Return the data in the exact JSON schema format provided.
""",
    
    "fighter_details": """
Extract detailed fighter information including:
- Full name parsing (first name, last name, nickname)
- Wikipedia URL from any links in the fighter's name cell
- Nationality from flag icons or country text
- Fight result (win/loss/draw/no contest)

Convert all relative Wikipedia URLs to absolute URLs.
""",
    
    "event_details": """
Extract event information from the infobox and first paragraph:
- Official event name and any variations mentioned
- Complete location details (venue, city, state, country)
- Event metrics (attendance, gate revenue, PPV buys)
- Date in YYYY-MM-DD format
- Any broadcast information
"""
}