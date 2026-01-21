import os
import json
import logging
from typing import List, Dict, Any
import anthropic

def extract_nominations_with_claude(text: str) -> List[Dict[str, Any]]:
	"""
	Extract nominations data from text using Anthropic Claude LLM.

	Args:
		text: The text to extract nominations from

	Returns:
	List of dicts with keys:
	- name_rank
	- name
	- rank
	- promotion_grade
	- new_assignment
	- current_assignment
	- location
        
	Raises:
		ValueError: If API key is not set
		APIError: If Claude API request fails
		JSONDecodeError: If Claude returns invalid JSON
	"""
	api_key = os.getenv("ANTHROPIC_API_KEY")
	if not api_key:
		raise ValueError("ANTHROPIC_API_KEY environment variable must be set")
    
	logging.info("API key successfully fetched")

	try:
		client = anthropic.Anthropic(api_key=api_key)
		model = "claude-sonnet-4-20250514"
		logging.info(f"Using model: {model}")

		# Prepare the prompt with better structure and examples
		prompt = f"""
            You are extracting structured nomination data from official text.

            Text:
            \"\"\"{text}\"\"\"

            Extract each nomination and return ONLY a valid JSON array of objects.
            Each object must have these exact keys (use empty string "" if not found):
            - "name_rank": Full name with rank/title
			- "name": Full name of the nominee
			- "rank": Rank or title of the nominee
            - "promotion_grade": Military grade being promoted to
            - "new_assignment": New position/assignment
            - "current_assignment": Current position/assignment  
            - "location": Geographic location or base

            Example output:
            [
            {{
                "name_rank": "Colonel John Smith",
				"name": "John Smith",
				"rank": "Colonel",
                "promotion_grade": "Brigadier General",
                "new_assignment": "Commander, 1st Brigade",
                "current_assignment": "Deputy Chief of Staff",
                "location": "Fort Bragg, NC"
            }}
            ]

            Return ONLY the JSON array. No markdown, comments, or extra text.
            If no nominations found, return [].
        """

		# Make API request with error handling
		response = client.messages.create(
			model=model,
			max_tokens=8000,
			temperature=0,
			messages=[{"role": "user", "content": prompt}]
		)

		# Extract and validate response
		content = response.content[0].text.strip()
		logging.info("Claude response received successfully")
        
		# Clean up any potential markdown formatting
		content = content.strip('`').strip()
		if content.startswith('json'):
			content = content[4:].strip()
        
		# Parse JSON with validation
		try:
			nominations = json.loads(content)
		except json.JSONDecodeError as e:
			logging.error(f"Invalid JSON from Claude: {content}")
			logging.error(f"JSON decode error: {e}")
			raise json.JSONDecodeError(f"Claude returned invalid JSON: {e}", content, 0)
        
		# Validate structure
		if not isinstance(nominations, list):
			logging.warning("Claude returned non-list, converting to list")
			nominations = [nominations] if nominations else []
        
		# Validate each nomination has required keys
		required_keys = {"name_rank", "name", "rank", "promotion_grade", "new_assignment", "current_assignment", "location"}
		cleaned_nominations = []

		for i, nomination in enumerate(nominations):
			if not isinstance(nomination, dict):
				logging.warning(f"Skipping non-dict nomination at index {i}: {nomination}")
				continue

			# Ensure all required keys exist with string values
			cleaned_nomination = {}
			for key in required_keys:
				value = nomination.get(key, "")
				cleaned_nomination[key] = str(value) if value is not None else ""
			# If name_rank is missing, synthesize from rank and name
			if not cleaned_nomination.get("name_rank"):
				cleaned_nomination["name_rank"] = f"{cleaned_nomination.get('rank','')} {cleaned_nomination.get('name','')}".strip()
			cleaned_nominations.append(cleaned_nomination)

		logging.info(f"Successfully extracted {len(cleaned_nominations)} nominations")
		return cleaned_nominations

	except anthropic.APIError as e:
		logging.error(f"Anthropic API error: {e}")
		raise
	except Exception as e:
		logging.error(f"Unexpected error in Claude extraction: {e}")
		raise
