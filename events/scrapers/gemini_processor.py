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
                "max_output_tokens": 8192,
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
            
            # Create response schema for structured output (compatible format)
            response_schema = self._create_gemini_schema()
            
            # Configure generation with schema
            generation_config = self.model._generation_config.copy()
            generation_config["response_schema"] = response_schema
            
            # Generate structured output
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=self.safety_settings
            )
            
            # Parse JSON response
            if response.text:
                try:
                    json_data = json.loads(response.text)
                    ufc_event = UFCEventSchema.model_validate(json_data)
                    
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
                    logger.debug(f"Raw response: {response.text[:500]}...")
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
        
        # Add main instruction
        sections.append(GEMINI_PROMPTS["event_extraction"])
        sections.append("")
        
        # Add HTML sections
        if scraped_data.first_paragraph_html:
            sections.append("=== FIRST PARAGRAPH ===")
            sections.append(scraped_data.first_paragraph_html)
            sections.append("")
        
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
        sections.append("=== EXTRACTION REQUIREMENTS ===")
        sections.append("1. Extract event name variations from the opening paragraph:")
        sections.append("   - Look for parenthetical names like '(also known as UFC Fight Night 245, UFC on ESPN+ 103 and UFC Vegas 99)'")
        sections.append("   - Extract each variation: ['UFC Fight Night 245', 'UFC on ESPN+ 103', 'UFC Vegas 99']")
        sections.append("   - Include the main event name and all parenthetical variations in name_variations array")
        sections.append("   - Remove 'also known as', parentheses, and 'and' - keep only the actual names")
        sections.append("2. Extract ALL fights from the results table in order")
        sections.append("3. Set fight_order: 1=main event, 2=co-main event, etc.")
        sections.append("4. Set fight_section based on the Wikipedia table section headers:")
        sections.append("   - For modern events: 'Main Card', 'Preliminary Card', 'Early Preliminary Card'")
        sections.append("   - For tournament events: 'Finals', 'Semifinals', 'Quarterfinals', 'Alternate bouts'")
        sections.append("   - For weight-specific tournaments: 'Lightweight Finals', 'Heavyweight Semifinals', etc.")
        sections.append("   - For championship bouts: 'UFC Heavyweight Championship', 'Lightweight Championship'")
        sections.append("   - Use the EXACT section header from Wikipedia as the fight_section value")
        sections.append("5. Identify main event and title fights correctly")
        sections.append("6. Extract fighter Wikipedia URLs from any href attributes")
        sections.append("7. Parse fighter names into first_name, last_name, nickname")
        sections.append("8. Extract nationality from flag icons or country indicators")
        sections.append("9. METHOD FORMATTING RULES:")
        sections.append("   - method should be ONLY: 'KO', 'TKO', 'Submission', 'Decision', etc.")
        sections.append("   - method_details should contain specifics: 'punches', 'rear-naked choke', 'unanimous', etc.")
        sections.append("   - NEVER include scorecards (49-45, etc.) in either field - ignore them completely")
        sections.append("10. Set fighter results correctly: winner gets 'win', loser gets 'loss'")
        sections.append("11. Return valid JSON matching the UFCEventSchema structure")
        sections.append("")
        
        return "\n".join(sections)
    
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
                    logger.info(f"✅ Event {i} processed successfully")
                else:
                    logger.warning(f"❌ Event {i} processing failed")
                    
            except Exception as e:
                logger.error(f"Error processing event {i} ({scraped_data.event_title}): {e}")
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