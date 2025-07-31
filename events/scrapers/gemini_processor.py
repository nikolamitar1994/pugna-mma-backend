"""
Gemini AI Processor for UFC Wikipedia Data Extraction
Uses Google's Gemini API with structured output to convert HTML to JSON
"""
import json
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .schemas import (
    UFCEventSchema, ScrapingResultSchema, 
    GEMINI_PROMPTS
)

logger = logging.getLogger(__name__)


class GeminiProcessor:
    """Gemini AI processor for UFC Wikipedia data extraction"""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        """
        Initialize Gemini processor
        
        Args:
            api_key: Google AI API key
            model_name: Gemini model to use
        """
        self.api_key = api_key
        self.model_name = model_name
        
        # Rate limiting
        self.request_delay = 1.0  # seconds between requests
        self.last_request_time = 0
        
        # Safety settings for data extraction
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        self._setup_gemini()
    
    def _setup_gemini(self):
        """Configure Gemini API"""
        try:
            genai.configure(api_key=self.api_key)
            
            # Initialize model with structured output configuration
            generation_config = {
                "temperature": 0.1,  # Low temperature for consistent extraction
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 16384,  # Increased from 8192 to handle larger events
                "response_mime_type": "application/json",
            }
            
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=generation_config,
                safety_settings=self.safety_settings
            )
            
            logger.info(f"Gemini model {self.model_name} configured successfully")
            
        except Exception as e:
            logger.error(f"Error configuring Gemini: {e}")
            raise
    
    def _rate_limit(self):
        """Apply rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def process_scraped_event(self, scraped_data: ScrapingResultSchema) -> Optional[UFCEventSchema]:
        """
        Process scraped Wikipedia HTML into structured UFC event data
        
        Args:
            scraped_data: Raw HTML sections from Wikipedia scraper
            
        Returns:
            UFCEventSchema with structured event data or None if processing failed
        """
        if not scraped_data.extraction_success:
            logger.warning(f"Skipping failed scraping result: {scraped_data.event_url}")
            return None
        
        logger.info(f"Processing {scraped_data.event_title} with Gemini AI")
        
        try:
            # Apply rate limiting
            self._rate_limit()
            
            # Create comprehensive prompt with all HTML sections
            prompt = self._build_extraction_prompt(scraped_data)
            
            # Try without response schema first to see if that's causing truncation
            generation_config = {
                "temperature": 0.1,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 32768,
                "response_mime_type": "application/json",  # Still request JSON format
            }
            
            logger.info(f"Generating content with max_output_tokens: {generation_config['max_output_tokens']} (no schema)")
            
            # Generate without strict schema enforcement
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=self.safety_settings
            )
            
            logger.info(f"Received response length: {len(response.text) if response.text else 0} characters")
            
            # Parse JSON response
            if response.text:
                try:
                    json_data = json.loads(response.text)
                    
                    # Debug: Log the JSON structure we received
                    logger.info(f"JSON structure type: {type(json_data)}")
                    if isinstance(json_data, list):
                        logger.warning("Received JSON array instead of object - extracting first item")
                        json_data = json_data[0] if json_data else {}
                    elif not isinstance(json_data, dict):
                        logger.error(f"Unexpected JSON type: {type(json_data)}")
                        return None
                    
                    # Log the keys we received
                    logger.info(f"JSON keys: {list(json_data.keys()) if isinstance(json_data, dict) else 'Not a dict'}")
                    
                    # Debug: Log event keys to see what's missing
                    if 'event' in json_data:
                        event_keys = list(json_data['event'].keys()) if isinstance(json_data['event'], dict) else []
                        logger.info(f"Event keys: {event_keys}")
                        
                        # Quick fix for common field name mismatches
                        event_data = json_data['event']
                        if 'location' not in event_data and 'venue' in event_data:
                            event_data['location'] = event_data['venue']
                            logger.info("Mapped 'venue' to 'location'")
                        
                        if 'wikipedia_url' not in event_data:
                            # Add the Wikipedia URL from the original request
                            event_data['wikipedia_url'] = scraped_data.event_url
                            logger.info("Added missing 'wikipedia_url'")
                    
                    ufc_event = UFCEventSchema.model_validate(json_data)
                    
                    # Debug logging for name variations and methods
                    logger.info(f"✅ Raw JSON response from Gemini (first 2000 chars): {response.text[:2000]}")
                    logger.info(f"✅ Parsed event name: '{ufc_event.event.name}'")
                    logger.info(f"✅ Raw event name variations from Gemini: {ufc_event.event.name_variations}")
                    logger.info(f"✅ Name variations count: {len(ufc_event.event.name_variations)}")
                    
                    # Debug logging for method extraction
                    logger.info("✅ Method extraction check:")
                    for i, fight in enumerate(ufc_event.fights[:3], 1):  # Check first 3 fights
                        logger.info(f"  Fight {i}: method='{fight.method}', method_details='{fight.method_details}'")
                        if not fight.method and not fight.method_details:
                            logger.warning(f"    ⚠️  Fight {i} has empty method fields!")
                    
                    # Debug logging for ending time and round extraction
                    logger.info("🕐 Ending time and round extraction check:")
                    for i, fight in enumerate(ufc_event.fights[:3], 1):  # Check first 3 fights
                        logger.info(f"  Fight {i}: ending_round={fight.ending_round}, ending_time='{fight.ending_time}'")
                        if fight.ending_round == 1 and fight.method and "decision" not in fight.method.lower():
                            logger.warning(f"    ⚠️  Fight {i} suspicious ending round (Round 1 for non-decision)")
                        if not fight.ending_time or fight.ending_time.strip() == "":
                            logger.warning(f"    ⚠️  Fight {i} has empty ending_time!")
                    
                    # Debug logging for all extracted fighters to catch name extraction errors
                    logger.info("🔍 All fighters extracted by Gemini:")
                    for i, fight in enumerate(ufc_event.fights, 1):
                        logger.info(f"  Fight {i}: '{fight.fighter1.first_name}' '{fight.fighter1.last_name}' vs '{fight.fighter2.first_name}' '{fight.fighter2.last_name}'")
                        
                        # Specifically check for potential Rodriguez confusion
                        if "rodriguez" in fight.fighter1.last_name.lower() or "rodriguez" in fight.fighter2.last_name.lower():
                            logger.warning(f"⚠️  Rodriguez fight detected - double check names!")
                            logger.warning(f"    Fighter1: {fight.fighter1.first_name} {fight.fighter1.last_name}")
                            logger.warning(f"    Fighter2: {fight.fighter2.first_name} {fight.fighter2.last_name}")
                    
                    # Debug logging for problematic fights
                    for fight in ufc_event.fights:
                        if fight.method and "decision" in fight.method.lower():
                            logger.info(f"Decision fight found: {fight.fighter1.first_name} {fight.fighter1.last_name} vs {fight.fighter2.first_name} {fight.fighter2.last_name}")
                            logger.info(f"  Winner name: '{fight.winner_name}'")
                            logger.info(f"  Fighter1 result: '{fight.fighter1.result}'")
                            logger.info(f"  Fighter2 result: '{fight.fighter2.result}'")
                    
                    # Add processing metadata
                    ufc_event.scraped_sections.update({
                        "infobox": bool(scraped_data.infobox_html),
                        "results_table": bool(scraped_data.results_table_html),
                        "bonus_awards": bool(scraped_data.bonus_awards_html),
                        "first_paragraph": bool(scraped_data.first_paragraph_html)
                    })
                    
                    logger.info(f"✅ Successfully processed {scraped_data.event_title} - {len(ufc_event.fights)} fights extracted")
                    return ufc_event
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error for {scraped_data.event_title}: {e}")
                    logger.error(f"Full raw response that failed to parse: {response.text}")
                    logger.error(f"Error occurred at character {e.pos}: '{response.text[max(0, e.pos-10):e.pos+10]}'")
                    
                    # Try to fix common JSON issues and retry
                    fixed_json = self._attempt_json_fix(response.text)
                    if fixed_json:
                        try:
                            json_data = json.loads(fixed_json)
                            logger.info("✅ Successfully fixed and parsed JSON after error")
                            ufc_event = UFCEventSchema.model_validate(json_data)
                            
                            # Continue with normal processing...
                            logger.info(f"✅ Raw event name variations from Gemini: {ufc_event.event.name_variations}")
                            logger.info(f"✅ Name variations count: {len(ufc_event.event.name_variations)}")
                            
                            ufc_event.scraped_sections.update({
                                "infobox": bool(scraped_data.infobox_html),
                                "results_table": bool(scraped_data.results_table_html),
                                "bonus_awards": bool(scraped_data.bonus_awards_html),
                                "first_paragraph": bool(scraped_data.first_paragraph_html)
                            })
                            
                            logger.info(f"✅ Successfully processed {scraped_data.event_title} - {len(ufc_event.fights)} fights extracted")
                            return ufc_event
                            
                        except Exception as retry_e:
                            logger.error(f"Failed to parse fixed JSON: {retry_e}")
                    
                    return None
                    
                except Exception as e:
                    logger.error(f"Validation error for {scraped_data.event_title}: {e}")
                    return None
            else:
                logger.warning(f"Empty response from Gemini for {scraped_data.event_title}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing {scraped_data.event_title}: {e}")
            return None
    
    def _build_extraction_prompt(self, scraped_data: ScrapingResultSchema) -> str:
        """Build comprehensive extraction prompt for Gemini"""
        
        sections = []
        
        # Event URL and title context
        sections.append(f"UFC EVENT: {scraped_data.event_title}")
        sections.append(f"Wikipedia URL: {scraped_data.event_url}")
        sections.append("")
        
        # Add main instruction - shorter to conserve tokens
        sections.append("Extract UFC event data into JSON format. CRITICAL: Complete ALL JSON fields, never truncate response.")
        sections.append("")
        sections.append("🏗️ REQUIRED JSON STRUCTURE:")
        sections.append("Return a single JSON OBJECT (not array) with this structure:")
        sections.append('{ "event": {...}, "fights": [...], "bonus_awards": [...] }')
        sections.append("")
        sections.append("🚨 REQUIRED event fields:")
        sections.append('- "name": event name')
        sections.append('- "date": event date') 
        sections.append('- "location": full location (e.g., "Sydney, Australia")')
        sections.append('- "wikipedia_url": the Wikipedia URL')
        sections.append("")
        
        # Add HTML sections - FIRST PARAGRAPH FIRST for name variations
        if scraped_data.first_paragraph_html:
            sections.append("=== 🔥 FIRST PARAGRAPH (EXTRACT NAME VARIATIONS) 🔥 ===")
            sections.append(scraped_data.first_paragraph_html)
            sections.append("")
            sections.append("👆 EXTRACT EVENT NAME VARIATIONS FROM ABOVE PARAGRAPH! Look for 'also known as' text.")
            sections.append("")
            
            # Debug log the first paragraph being sent to Gemini
            logger.info(f"🔍 First paragraph HTML being sent to Gemini: {scraped_data.first_paragraph_html[:500]}...")
            
            # Check if the paragraph contains "also known as" text
            if 'also known as' in scraped_data.first_paragraph_html.lower():
                logger.info("✅ First paragraph contains 'also known as' text - name variations should be extracted")
            else:
                logger.warning("⚠️  First paragraph does NOT contain 'also known as' text")
        else:
            logger.warning("❌ No first paragraph HTML available for name variation extraction!")
        
        if scraped_data.infobox_html:
            sections.append("=== EVENT INFOBOX ===")
            sections.append(scraped_data.infobox_html)
            sections.append("")
        
        if scraped_data.results_table_html:
            sections.append("=== FIGHT RESULTS TABLE ===")
            sections.append(scraped_data.results_table_html)
            sections.append("")
            sections.append("IMPORTANT: Extract fighter Wikipedia URLs from href attributes.")
            sections.append("Convert relative URLs (/wiki/...) to absolute (https://en.wikipedia.org/wiki/...)")
            sections.append("")
        
        if scraped_data.bonus_awards_html:
            sections.append("=== BONUS AWARDS ===")
            sections.append(scraped_data.bonus_awards_html)
            sections.append("")
        
        # Add specific extraction instructions
        sections.append("=== CRITICAL: NAME VARIATIONS EXTRACTION ===")
        sections.append("STEP 1: Find the first paragraph and look for 'also known as' text")
        sections.append("STEP 2: Extract ALL event name variations from parenthetical text")
        sections.append("")
        sections.append("Example paragraph:")
        sections.append("'UFC Fight Night: Magny vs. Prates (also known as UFC Fight Night 247, UFC Vegas 100, and UFC on ESPN+ 105) was a mixed martial arts event...'")
        sections.append("")
        sections.append("REQUIRED JSON OUTPUT for name_variations field:")
        sections.append('["UFC Fight Night: Magny vs. Prates", "UFC Fight Night 247", "UFC Vegas 100", "UFC on ESPN+ 105"]')
        sections.append("")
        sections.append("PARSING STEPS:")
        sections.append("1. Find text in parentheses after 'also known as'")
        sections.append("2. Split by commas: 'UFC Fight Night 247', 'UFC Vegas 100', 'and UFC on ESPN+ 105'") 
        sections.append("3. Remove 'and' from last item: 'UFC on ESPN+ 105'")
        sections.append("4. Add main title as first element")
        sections.append("5. Result: 4 clean names in array")
        sections.append("")
        sections.append("EXTRACTION RULES:")
        sections.append("- Split on commas and 'and' to separate each name")
        sections.append("- Remove 'also known as', parentheses, and connecting words")
        sections.append("- Clean whitespace from each name")
        sections.append("- ALWAYS include the main title as the first item")
        sections.append("- Return empty array ONLY if no variations exist")
        sections.append("")
        sections.append("🚨 MORE EXAMPLES of name variation extraction:")
        sections.append("   Example 1: '(also known as UFC Fight Night 249, UFC Vegas 101, and UFC on ESPN+ 107)'")
        sections.append("   Extract: ['Main Event Name', 'UFC Fight Night 249', 'UFC Vegas 101', 'UFC on ESPN+ 107']")
        sections.append("")
        sections.append("   Example 2: '(also known as UFC Fight Night 247, UFC Vegas 100, and UFC on ESPN+ 105)'")
        sections.append("   Extract: ['Main Event Name', 'UFC Fight Night 247', 'UFC Vegas 100', 'UFC on ESPN+ 105']")
        sections.append("")
        sections.append("🚨 FALLBACK INSTRUCTIONS IF FIRST PARAGRAPH DOESN'T HAVE 'also known as':")
        sections.append("- Check if the event name contains patterns like 'UFC Fight Night 248' or 'UFC on ESPN+'")
        sections.append("- Look for numbered UFC Fight Night events or network identifiers") 
        sections.append("- Extract any obvious alternative naming patterns")
        sections.append("- If truly no variations exist, include at least the main event name in the array")
        sections.append("")
        sections.append("=== OTHER EXTRACTION REQUIREMENTS ===")
        sections.append("2. Extract ALL fights from the results table in order")
        sections.append("3. COMPLETE FIGHT OBJECT EXAMPLE:")
        sections.append("   {")
        sections.append('     "fight_order": 1,')
        sections.append('     "fight_section": "Main Card",')
        sections.append('     "is_main_event": true,')
        sections.append('     "is_title_fight": false,')
        sections.append('     "weight_class": "Middleweight",')
        sections.append('     "scheduled_rounds": 5,')
        sections.append('     "fighter1": {')
        sections.append('       "first_name": "Roman",')
        sections.append('       "last_name": "Dolidze",')
        sections.append('       "nickname": "",')
        sections.append('       "wikipedia_url": "https://en.wikipedia.org/wiki/Roman_Dolidze",')
        sections.append('       "nationality": "Georgia",')
        sections.append('       "result": ""')
        sections.append('     },')
        sections.append('     "fighter2": {')
        sections.append('       "first_name": "Anthony",')
        sections.append('       "last_name": "Hernandez",')
        sections.append('       "nickname": "",')
        sections.append('       "wikipedia_url": "https://en.wikipedia.org/wiki/Anthony_Hernandez",')
        sections.append('       "nationality": "USA",')
        sections.append('       "result": ""')
        sections.append('     },')
        sections.append('     "winner_name": "",')
        sections.append('     "method": "",')
        sections.append('     "method_details": "",')
        sections.append('     "ending_round": 1,')
        sections.append('     "ending_time": "",')
        sections.append('     "referee": "",')
        sections.append('     "notes": ""')
        sections.append("   }")
        sections.append("3. Set fight_order: 1=main event, 2=co-main event, etc.")
        sections.append("4. Set fight_section based on the Wikipedia table section headers:")
        sections.append("   - For modern events: 'Main Card', 'Preliminary Card', 'Early Preliminary Card'")
        sections.append("   - For tournament events: 'Finals', 'Semifinals', 'Quarterfinals', 'Alternate bouts'")
        sections.append("   - For weight-specific tournaments: 'Lightweight Finals', 'Heavyweight Semifinals', etc.")
        sections.append("   - For championship bouts: 'UFC Heavyweight Championship', 'Lightweight Championship'")
        sections.append("   - Use the EXACT section header from Wikipedia as the fight_section value")
        sections.append("5. Identify main event and title fights correctly")
        sections.append("6. Extract fighter Wikipedia URLs from any href attributes")
        sections.append("7. FIGHTER OBJECT STRUCTURE - CRITICAL:")
        sections.append("   🚨 Each fighter MUST be an OBJECT with these fields:")
        sections.append("   {")
        sections.append('     "first_name": "Roman",')
        sections.append('     "last_name": "Dolidze",')
        sections.append('     "nickname": "",')
        sections.append('     "wikipedia_url": "https://en.wikipedia.org/wiki/Roman_Dolidze",')
        sections.append('     "nationality": "Georgia",')
        sections.append('     "result": ""')
        sections.append("   }")
        sections.append("   🚨 NEVER use just a string like 'Roman Dolidze' - ALWAYS use the full object structure")
        sections.append("   🚨 Parse fighter names into first_name, last_name, nickname")
        sections.append("   🚨 Extract fighter names EXACTLY as they appear in the table")
        sections.append("   🚨 Do NOT substitute or change any names - use the EXACT spelling from Wikipedia")
        sections.append("   🚨 Do NOT confuse similar names - 'Piera' is NOT 'Yair'")
        sections.append("   🚨 Read character by character if needed - P-I-E-R-A is different from Y-A-I-R")
        sections.append("   🚨 If you see 'Piera Rodríguez', extract 'Piera', NOT 'Yair'")
        sections.append("8. Extract nationality from flag icons or country indicators")
        sections.append("9. METHOD FORMATTING RULES - CRITICAL:")
        sections.append("   🚨 ALWAYS extract method and method_details for EVERY fight")
        sections.append("   🚨 method should be ONLY: 'KO', 'TKO', 'Submission', 'Decision', etc.")
        sections.append("   🚨 method_details should contain specifics: 'punches', 'rear-naked choke', 'unanimous', etc.")
        sections.append("   🚨 EXAMPLES of correct extraction:")
        sections.append("     * 'Submission (armbar)' -> method='Submission', method_details='armbar'")
        sections.append("     * 'TKO (punches)' -> method='TKO', method_details='punches'")
        sections.append("     * 'KO (left hook)' -> method='KO', method_details='left hook'")
        sections.append("     * 'Decision (unanimous)' -> method='Decision', method_details='unanimous'")
        sections.append("   🚨 NEVER leave method or method_details empty if data exists in Wikipedia")
        sections.append("   🚨 NEVER include scorecards (49-45, etc.) in either field - ignore them completely")
        sections.append("10. ENDING TIME AND ROUND EXTRACTION - CRITICAL:")
        sections.append("   🚨 ALWAYS extract ending_time and ending_round for EVERY fight")
        sections.append("   🚨 Wikipedia format examples: 'TKO (punches), Round 2, 3:45' or 'Submission (armbar), Round 1, 2:34'")
        sections.append("   🚨 Extract ending_round as integer: 'Round 2' -> ending_round=2")
        sections.append("   🚨 Extract ending_time as MM:SS string: '3:45' -> ending_time='3:45'")
        sections.append("   🚨 PARSING EXAMPLES:")
        sections.append("     * 'TKO (punches), Round 2, 3:45' -> method='TKO', method_details='punches', ending_round=2, ending_time='3:45'")
        sections.append("     * 'Decision (unanimous), Round 3, 5:00' -> method='Decision', method_details='unanimous', ending_round=3, ending_time='5:00'")
        sections.append("     * 'KO (left hook), Round 1, 4:16' -> method='KO', method_details='left hook', ending_round=1, ending_time='4:16'")
        sections.append("   🚨 For Decision fights: ending_round should be 3 or 5 (full fight), ending_time should be '5:00'")
        sections.append("   🚨 For early finishes: ending_round is the actual round, ending_time is when it ended")
        sections.append("   🚨 If time/round info is missing in Wikipedia, default: ending_round=1, ending_time=''")
        sections.append("   🚨 NEVER leave ending_round empty - it must be an integer 1, 2, 3, 4, or 5")
        sections.append("11. FIGHTER RESULTS HANDLING:")
        sections.append("   🚨 For COMPLETED fights: winner gets 'win', loser gets 'loss', draw gets 'draw'")
        sections.append("   🚨 For UPCOMING/SCHEDULED fights (no results yet): set result='' (empty string) for all fighters")
        sections.append("   🚨 How to detect upcoming fights: Method, Round, Time columns are empty or contain no data")
        sections.append("   🚨 EXAMPLES:")
        sections.append("     * Completed: 'TKO (punches), Round 2, 3:45' -> winner result='win', loser result='loss'")
        sections.append("     * Upcoming: Empty method/round/time -> both fighters result='' (empty string)")
        sections.append("12. ANNOUNCED BOUTS HANDLING - CRITICAL:")
        sections.append("   🚨 ALWAYS check for 'ANNOUNCED BOUTS SECTION' comment in the HTML")
        sections.append("   🚨 Parse announced bouts from text like 'Bantamweight bout: Steve Erceg vs. Ode\\' Osbourne'")
        sections.append("   🚨 Extract weight class, fighter names, and create fight objects")
        sections.append("   🚨 PARSING EXAMPLES:")
        sections.append("     * 'Bantamweight bout: Steve Erceg vs. Ode\\' Osbourne' -> weight_class='Bantamweight', fighter1='Steve Erceg', fighter2='Ode\\' Osbourne'") 
        sections.append("     * 'Welterweight bout: Uros Medic vs. Gilbert Urbina' -> weight_class='Welterweight', fighter1='Uros Medic', fighter2='Gilbert Urbina'")
        sections.append("   🚨 Set fight_section to 'Announced Bouts'")
        sections.append("   🚨 Assign fight_order numbers continuing from main card (e.g., if main card ends at 9, start at 10)")
        sections.append("   🚨 All announced bout fighters get result='' (empty string)")
        sections.append("   🚨 No method, ending_round=1, ending_time='' for announced bouts")
        sections.append("   🚨 NEVER use null - always use empty strings '' for missing data")
        sections.append("13. BONUS AWARDS EXTRACTION - CRITICAL:")
        sections.append("   🚨 ALWAYS extract bonus awards as OBJECTS, NEVER as strings")
        sections.append("   🚨 BONUS AWARD OBJECT STRUCTURE - REQUIRED:")
        sections.append("   {")
        sections.append('     "award_type": "Fight of the Night",')
        sections.append('     "fighter_name": "Justin Gaethje",')
        sections.append('     "amount": 50000')
        sections.append("   }")
        sections.append("   🚨 PARSING EXAMPLES:")
        sections.append("     * 'Fight of the Night: Justin Gaethje vs. Rafael Fiziev' ->")
        sections.append("       [")
        sections.append('         {"award_type": "Fight of the Night", "fighter_name": "Justin Gaethje", "amount": 50000},')
        sections.append('         {"award_type": "Fight of the Night", "fighter_name": "Rafael Fiziev", "amount": 50000}')
        sections.append("       ]")
        sections.append("     * 'Performance of the Night: Roman Dolidze' ->")
        sections.append('       [{"award_type": "Performance of the Night", "fighter_name": "Roman Dolidze", "amount": 50000}]')
        sections.append("   🚨 BONUS AWARD TYPES:")
        sections.append("     - 'Fight of the Night' (2 fighters get this award)")
        sections.append("     - 'Performance of the Night' (1 fighter gets this award)")
        sections.append("     - 'Submission of the Night' (1 fighter gets this award)")
        sections.append("     - 'Knockout of the Night' (1 fighter gets this award)")
        sections.append("   🚨 NEVER return bonus awards as strings like 'Fight of the Night: Fighter vs Fighter'")
        sections.append("   🚨 ALWAYS break down into individual fighter objects with award_type, fighter_name, amount")
        sections.append("   🚨 Default amount is 50000 unless specified otherwise")
        sections.append("   🚨 If no bonus awards exist, use empty array: []")
        sections.append("14. TEXT EXTRACTION RULES:")
        sections.append("   - Extract ONLY clean text, no HTML tags or markup")
        sections.append("   - venue should be just the venue name (e.g., 'UFC Apex', not HTML links)")
        sections.append("   - All text fields should be concise and clean")
        sections.append("   - Remove excessive whitespace and normalize text")
        sections.append("15. JSON FORMATTING RULES - CRITICAL:")
        sections.append("   🚨 Return COMPLETE VALID JSON matching the UFCEventSchema structure")
        sections.append("   🚨 NEVER truncate or cut off the JSON response - complete ALL fields")
        sections.append("   🚨 ESCAPE all quotes and special characters in strings")
        sections.append("   🚨 Use double quotes for all JSON strings, not single quotes") 
        sections.append("   🚨 Ensure all strings are properly closed with quotes")
        sections.append("   🚨 NEVER use null values - use empty strings \"\" instead")
        sections.append("   🚨 For missing method: \"method\": \"\", NOT \"method\": null")
        sections.append("   🚨 End with proper closing braces: } or }]")
        sections.append("   🚨 If response is too long, prioritize completing the JSON structure")
        sections.append("   🚨 Test JSON validity before returning - malformed JSON will cause errors")
        sections.append("")
        sections.append("🚨🚨🚨 FINAL REMINDER: COMPLETE THE ENTIRE JSON RESPONSE! DO NOT STOP MID-STRING! 🚨🚨🚨")
        sections.append("Your response MUST be a complete, valid JSON object that ends with }")
        sections.append("")
        
        return "\n".join(sections)
    
    def _attempt_json_fix(self, broken_json: str) -> Optional[str]:
        """Attempt to fix common JSON formatting issues"""
        try:
            import re
            fixed = broken_json.strip()
            
            logger.info(f"Attempting to fix JSON. Original length: {len(broken_json)}")
            
            # Handle the specific pattern we're seeing: truncated venue field
            if '"venue": "anb Arena' in fixed and not fixed.endswith('"'):
                logger.info("Detected specific venue truncation pattern")
                
                # Simple fix: just add the missing quote and minimal structure to make valid JSON
                if '"venue": "anb Arena' in fixed:
                    # Add closing quote for venue
                    fixed = fixed.replace('"venue": "anb Arena', '"venue": "anb Arena"')
                    logger.info("Added missing venue closing quote")
                
                # Ensure minimal valid JSON structure
                if not fixed.rstrip().endswith('}'):
                    # Count unclosed braces
                    open_braces = fixed.count('{') - fixed.count('}')
                    if open_braces > 0:
                        fixed = fixed.rstrip()
                        if not fixed.endswith(','):
                            fixed += ','
                        # Add minimal required fields to close the event object
                        fixed += '"name_variations":[]'
                        fixed += '}' * open_braces
                        logger.info("Added minimal closing structure")
                
                # Try to validate
                json.loads(fixed)
                logger.info("✅ Successfully fixed JSON with simple approach")
                return fixed
            
            # Fallback for other truncation patterns
            logger.info("Trying general truncation fixes")
            
            # Find last quote and see if we need to close it
            last_quote_pos = fixed.rfind('"')
            if last_quote_pos != -1:
                # Check if the quote is opening or closing by counting quotes before it
                quotes_before = fixed[:last_quote_pos].count('"')
                if quotes_before % 2 == 1:  # Odd number means this should be a closing quote
                    # We need another quote to close the string
                    fixed = fixed + '"'
                    logger.info("Added missing closing quote")
            
            # Close any unclosed braces
            open_braces = fixed.count('{') - fixed.count('}')
            if open_braces > 0:
                # Make sure we properly close the truncated string first
                if not fixed.rstrip().endswith(('"', ',', '{', '[')):
                    fixed = fixed.rstrip() + '"'  # Close the truncated string
                    logger.info("Added closing quote for truncated string")
                
                if not fixed.rstrip().endswith((',', '{', '[')):
                    fixed = fixed.rstrip() + ','
                    logger.info("Added comma separator")
                
                fixed += '"name_variations":[]'  # Add minimal required field
                fixed += '}' * open_braces
                logger.info(f"Closed {open_braces} open braces")
            
            # Validate
            json.loads(fixed)
            logger.info("✅ Successfully fixed JSON with general approach")
            return fixed
            
        except Exception as e:
            logger.error(f"Failed to fix JSON: {e}")
            logger.info(f"Final fixed attempt (first 500 chars): {fixed[:500]}")
            return None
    
    def _create_gemini_schema(self) -> Dict[str, Any]:
        """Create Gemini-compatible JSON schema without $defs"""
        return {
            "type": "object",
            "properties": {
                "event": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "date": {"type": "string"},
                        "location": {"type": "string"},
                        "venue": {"type": "string"},
                        "city": {"type": "string"},
                        "state": {"type": "string"},
                        "country": {"type": "string"},
                        "wikipedia_url": {"type": "string"},
                        "event_number": {"type": "integer"},
                        "attendance": {"type": "integer"},
                        "gate_revenue": {"type": "number"},
                        "ppv_buys": {"type": "integer"},
                        "name_variations": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["name", "date", "location", "wikipedia_url"]
                },
                "fights": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "fight_order": {"type": "integer"},
                            "fight_section": {"type": "string"},
                            "is_main_event": {"type": "boolean"},
                            "is_title_fight": {"type": "boolean"},
                            "weight_class": {"type": "string"},
                            "scheduled_rounds": {"type": "integer"},
                            "method": {"type": "string"},
                            "method_details": {"type": "string"},
                            "ending_round": {"type": "integer"},
                            "ending_time": {"type": "string"},
                            "referee": {"type": "string"},
                            "winner_name": {"type": "string"},
                            "notes": {"type": "string"},
                            "fighter1": {
                                "type": "object",
                                "properties": {
                                    "first_name": {"type": "string"},
                                    "last_name": {"type": "string"},
                                    "nickname": {"type": "string"},
                                    "wikipedia_url": {"type": "string"},
                                    "nationality": {"type": "string"},
                                    "result": {"type": "string", "enum": ["win", "loss", "draw", "no_contest"]}
                                },
                                "required": ["first_name", "result"]
                            },
                            "fighter2": {
                                "type": "object",
                                "properties": {
                                    "first_name": {"type": "string"},
                                    "last_name": {"type": "string"},
                                    "nickname": {"type": "string"},
                                    "wikipedia_url": {"type": "string"},
                                    "nationality": {"type": "string"},
                                    "result": {"type": "string", "enum": ["win", "loss", "draw", "no_contest"]}
                                },
                                "required": ["first_name", "result"]
                            }
                        },
                        "required": ["fight_order", "fighter1", "fighter2"]
                    }
                },
                "bonus_awards": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "award_type": {"type": "string"},
                            "fighter_name": {"type": "string"},
                            "amount": {"type": "number"},
                            "description": {"type": "string"}
                        },
                        "required": ["award_type", "fighter_name"]
                    }
                }
            },
            "required": ["event", "fights"]
        }
    
    def batch_process_events(self, scraped_results: List[ScrapingResultSchema]) -> List[UFCEventSchema]:
        """
        Process multiple scraped events in batch with rate limiting
        
        Args:
            scraped_results: List of scraped Wikipedia data
            
        Returns:
            List of processed UFC events (skips failed processing)
        """
        processed_events = []
        total_events = len(scraped_results)
        
        logger.info(f"Starting batch processing of {total_events} events with Gemini AI")
        
        for i, scraped_data in enumerate(scraped_results, 1):
            logger.info(f"Processing event {i}/{total_events}: {scraped_data.event_title}")
            
            try:
                ufc_event = self.process_scraped_event(scraped_data)
                
                if ufc_event:
                    processed_events.append(ufc_event)
                    logger.info(f"✅ Event {i} processed successfully: {ufc_event.event.name}")
                else:
                    logger.warning(f"❌ Event {i} processing failed: {scraped_data.event_title}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing event {i} ({scraped_data.event_title}): {e}")
                # Log more details for debugging
                logger.error(f"   Event URL: {scraped_data.event_url}")
                logger.error(f"   Extraction success: {scraped_data.extraction_success}")
                logger.error(f"   Error messages: {scraped_data.error_messages}")
                continue
        
        success_rate = len(processed_events) / total_events * 100
        logger.info(f"Batch processing completed: {len(processed_events)}/{total_events} events processed ({success_rate:.1f}% success rate)")
        
        return processed_events
    
    def validate_extraction_quality(self, ufc_event: UFCEventSchema) -> Dict[str, Any]:
        """
        Validate the quality of extracted data
        
        Returns:
            Quality metrics and validation results
        """
        quality_report = {
            "event_completeness": 0.0,
            "fight_completeness": 0.0,
            "fighter_data_quality": 0.0,
            "wikipedia_urls_found": 0,
            "total_fighters": 0,
            "warnings": [],
            "overall_score": 0.0
        }
        
        try:
            # Check event data completeness
            event_fields = ["name", "date", "location"]
            event_complete_fields = sum(1 for field in event_fields if getattr(ufc_event.event, field, None))
            quality_report["event_completeness"] = event_complete_fields / len(event_fields)
            
            # Check fight data completeness
            if ufc_event.fights:
                total_fights = len(ufc_event.fights)
                complete_fights = 0
                wikipedia_urls = 0
                total_fighters = 0
                
                required_fight_fields = ["fighter1", "fighter2", "weight_class"]
                
                for fight in ufc_event.fights:
                    # Count complete fights
                    complete_fields = sum(1 for field in required_fight_fields if getattr(fight, field, None))
                    if complete_fields == len(required_fight_fields):
                        complete_fights += 1
                    
                    # Count fighter data quality
                    for fighter in [fight.fighter1, fight.fighter2]:
                        total_fighters += 1
                        if fighter.wikipedia_url:
                            wikipedia_urls += 1
                
                quality_report["fight_completeness"] = complete_fights / total_fights if total_fights > 0 else 0
                quality_report["wikipedia_urls_found"] = wikipedia_urls
                quality_report["total_fighters"] = total_fighters
                quality_report["fighter_data_quality"] = wikipedia_urls / total_fighters if total_fighters > 0 else 0
            
            # Generate warnings
            if quality_report["event_completeness"] < 0.8:
                quality_report["warnings"].append("Event data incomplete")
            
            if quality_report["fight_completeness"] < 0.8:
                quality_report["warnings"].append("Fight data incomplete")
            
            if quality_report["fighter_data_quality"] < 0.5:
                quality_report["warnings"].append("Few fighter Wikipedia URLs found")
            
            # Calculate overall score
            scores = [
                quality_report["event_completeness"],
                quality_report["fight_completeness"], 
                quality_report["fighter_data_quality"]
            ]
            quality_report["overall_score"] = sum(scores) / len(scores)
            
        except Exception as e:
            logger.error(f"Error validating extraction quality: {e}")
            quality_report["warnings"].append(f"Validation error: {str(e)}")
        
        return quality_report