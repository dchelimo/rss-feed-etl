"""
Military-focused extractor for US military personnel changes.
Handles both official announcements and news coverage of military personnel updates.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import anthropic
from config.extraction_schemas import (
    MilitaryArticleType, ExtractionSchema, get_schema_for_article_type, 
    detect_military_article_type, is_military_personnel_article, MILITARY_EXTRACTION_SCHEMAS
)

logger = logging.getLogger(__name__)

class MilitaryPersonnelExtractor:
    """Specialized extractor for US military personnel changes using Claude"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY must be provided or set as environment variable")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"
    
    def extract_military_personnel_data(
        self, 
        text: str, 
        title: str = "", 
        summary: str = "",
        article_type: Optional[MilitaryArticleType] = None,
        custom_schema: Optional[ExtractionSchema] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from military personnel articles.
        
        Args:
            text: Full article text
            title: Article title (helps with type detection)
            summary: Article summary (helps with type detection)
            article_type: Force specific military article type (optional)
            custom_schema: Use custom extraction schema (optional)
            
        Returns:
            Dict with extracted military personnel data, metadata, and confidence scores
        """
        
        # First check if this is actually about military personnel
        if not is_military_personnel_article(title, summary, text):
            logger.info("Article does not appear to be about military personnel changes")
            return {
                "is_military_personnel": False,
                "extraction_confidence": 0.0,
                "extracted_entities": [],
                "processing_metadata": {"status": "not_military_personnel"}
            }
        
        # Determine military article type
        if article_type is None:
            article_type = detect_military_article_type(title, summary, text)
        
        # Get extraction schema
        if custom_schema:
            schema = custom_schema
        else:
            schema = get_schema_for_article_type(article_type)
        
        logger.info(f"Processing military article as type: {article_type.value}")
        logger.info(f"Using schema: {schema.description}")
        
        try:
            # Generate military-focused prompt based on schema
            extracted_data = self._extract_with_military_schema(text, title, summary, schema)
            
            # Add military-specific metadata
            result = {
                "is_military_personnel": True,
                "military_article_type": article_type.value,
                "schema_used": schema.description,
                "extraction_confidence": self._calculate_confidence(extracted_data, schema),
                "extracted_personnel": extracted_data,
                "military_metadata": {
                    "model_used": self.model,
                    "schema_version": "1.0",
                    "field_count": len(schema.fields),
                    "personnel_count": len(extracted_data)
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Military extraction failed for article type {article_type.value}: {e}")
            return {
                "is_military_personnel": True,
                "military_article_type": article_type.value,
                "extraction_confidence": 0.0,
                "extracted_personnel": [],
                "error": str(e),
                "processing_metadata": {"status": "extraction_failed"}
            }
    
    def _extract_with_military_schema(
        self, 
        text: str, 
        title: str, 
        summary: str, 
        schema: ExtractionSchema
    ) -> List[Dict[str, Any]]:
        """Extract military personnel data using a specific schema"""
        
        # Build field descriptions for the prompt
        field_descriptions = "\n".join([
            f'- "{field_name}": {description}'
            for field_name, description in schema.fields.items()
        ])
        
        # Create military-focused prompt
        prompt = f"""
You are extracting US military personnel information from an article about military personnel changes.

Article Type: {schema.description}
Title: {title}
Summary: {summary}

Article Text:
\"\"\"
{text}
\"\"\"

{schema.prompt_template}

IMPORTANT INSTRUCTIONS:
1. Only extract information about US military personnel (Army, Navy, Air Force, Marines, Space Force, Coast Guard)
2. Focus on personnel changes: promotions, assignments, retirements, command changes
3. Be precise with military ranks and titles
4. Include service branch for each person when possible
5. Extract information for each person mentioned individually

Extract information and return ONLY a valid JSON array of objects.
Each object must have these exact keys (use empty string "" if not found):
{field_descriptions}

Example output format:
[
{json.dumps(schema.example_output, indent=2)}
]

Rules:
1. Return ONLY the JSON array, no markdown or comments
2. If no military personnel changes found, return []
3. Extract multiple personnel if present (separate object for each person)
4. Be precise and factual - don't infer information not clearly stated
5. Use empty string "" for missing information, not null or undefined
6. Ensure each person gets their own object in the array

Return ONLY the JSON array:
"""

        # Make API request
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse response
        content = response.content[0].text.strip()
        logger.info("Claude response received successfully")
        
        # Clean up formatting
        content = content.strip('`').strip()
        if content.startswith('json'):
            content = content[4:].strip()
        
        try:
            extracted_data = json.loads(content)
            if not isinstance(extracted_data, list):
                extracted_data = [extracted_data] if extracted_data else []
            
            # Validate extracted data against schema
            validated_data = self._validate_military_data(extracted_data, schema)
            
            logger.info(f"Successfully extracted {len(validated_data)} military personnel")
            return validated_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from Claude: {content}")
            raise json.JSONDecodeError(f"Claude returned invalid JSON: {e}", content, 0)
    
    def _validate_military_data(
        self, 
        extracted_data: List[Dict], 
        schema: ExtractionSchema
    ) -> List[Dict[str, Any]]:
        """Validate and clean extracted military personnel data according to schema"""
        
        validated_personnel = []
        
        for i, person in enumerate(extracted_data):
            if not isinstance(person, dict):
                logger.warning(f"Skipping non-dict personnel entry at index {i}: {person}")
                continue
            
            # Ensure all required fields exist
            validated_person = {}
            for field_name in schema.fields.keys():
                value = person.get(field_name, "")
                validated_person[field_name] = str(value) if value is not None else ""
            
            # Add any extra fields that might be useful
            for field_name, value in person.items():
                if field_name not in validated_person:
                    validated_person[f"extra_{field_name}"] = str(value) if value is not None else ""
            
            # Military-specific validation
            validated_person = self._apply_military_validation(validated_person)
            
            validated_personnel.append(validated_person)
        
        return validated_personnel
    
    def _apply_military_validation(self, person_data: Dict[str, str]) -> Dict[str, str]:
        """Apply military-specific validation and standardization"""
        
        # Standardize service branch names
        service_mapping = {
            "us army": "Army",
            "u.s. army": "Army", 
            "united states army": "Army",
            "us navy": "Navy",
            "u.s. navy": "Navy",
            "united states navy": "Navy",
            "us air force": "Air Force",
            "u.s. air force": "Air Force", 
            "united states air force": "Air Force",
            "us marines": "Marines",
            "u.s. marines": "Marines",
            "marine corps": "Marines",
            "us marine corps": "Marines",
            "space force": "Space Force",
            "u.s. space force": "Space Force",
            "coast guard": "Coast Guard",
            "u.s. coast guard": "Coast Guard"
        }
        
        service_branch = person_data.get("service_branch", "").lower()
        for key, standardized in service_mapping.items():
            if key in service_branch:
                person_data["service_branch"] = standardized
                break
        
        # Standardize announcement types
        if "announcement_type" in person_data:
            announcement_type = person_data["announcement_type"].lower()
            if "promotion" in announcement_type and "assignment" in announcement_type:
                person_data["announcement_type"] = "promotion_and_assignment"
            elif "promotion" in announcement_type:
                person_data["announcement_type"] = "promotion"
            elif "assignment" in announcement_type or "command" in announcement_type:
                person_data["announcement_type"] = "assignment"
            elif "retirement" in announcement_type:
                person_data["announcement_type"] = "retirement"
        
        return person_data
    
    def _calculate_confidence(
        self, 
        extracted_data: List[Dict], 
        schema: ExtractionSchema
    ) -> float:
        """Calculate confidence score for military extraction quality"""
        
        if not extracted_data:
            return 0.0
        
        total_confidence = 0.0
        
        for person in extracted_data:
            # Core military fields that should be present
            core_fields = ["name", "rank", "service_branch"]
            core_filled = sum(1 for field in core_fields if person.get(field, "").strip())
            
            # All fields
            filled_fields = sum(1 for value in person.values() if value.strip())
            total_fields = len(schema.fields)
            
            # Weight core fields more heavily
            core_weight = 0.6
            general_weight = 0.4
            
            core_confidence = core_filled / len(core_fields) if core_fields else 0.0
            general_confidence = filled_fields / total_fields if total_fields > 0 else 0.0
            
            person_confidence = (core_confidence * core_weight) + (general_confidence * general_weight)
            total_confidence += person_confidence
        
        average_confidence = total_confidence / len(extracted_data)
        return round(average_confidence, 3)

# Legacy function for backward compatibility
def extract_nominations_with_claude(text: str) -> List[Dict[str, Any]]:
    """
    Legacy function for military nominations - maintains backward compatibility
    """
    extractor = MilitaryPersonnelExtractor()
    result = extractor.extract_military_personnel_data(
        text=text,
        article_type=MilitaryArticleType.OFFICIAL_ANNOUNCEMENTS
    )
    return result.get("extracted_personnel", [])

# Enhanced function for military article extraction
def extract_military_personnel(
    text: str, 
    title: str = "", 
    summary: str = "",
    article_type: str = None
) -> Dict[str, Any]:
    """
    Enhanced function to extract data from military personnel articles.
    
    Args:
        text: Article content
        title: Article title
        summary: Article summary  
        article_type: Optional military article type (official_announcements, news_coverage, etc.)
        
    Returns:
        Dictionary with extracted military personnel data and metadata
    """
    extractor = MilitaryPersonnelExtractor()
    
    # Convert string article_type to enum if provided
    type_enum = None
    if article_type:
        try:
            type_enum = MilitaryArticleType(article_type)
        except ValueError:
            logger.warning(f"Unknown military article type '{article_type}', using auto-detection")
    
    return extractor.extract_military_personnel_data(
        text=text,
        title=title,
        summary=summary,
        article_type=type_enum
    )