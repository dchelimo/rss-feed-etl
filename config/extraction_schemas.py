"""
Military-focused extraction schemas for US military personnel changes.
Handles both official announcements and news coverage of military personnel updates.
"""

from enum import Enum
from typing import Dict, List, Any
from dataclasses import dataclass

class MilitaryArticleType(Enum):
    """Types of military-related articles we can process"""
    OFFICIAL_ANNOUNCEMENTS = "official_announcements"  # Official DoD/service announcements
    NEWS_COVERAGE = "news_coverage"  # News articles about military changes
    PROMOTION_CEREMONIES = "promotion_ceremonies"  # Ceremony coverage
    RETIREMENT_ANNOUNCEMENTS = "retirement_announcements"  # Retirement notices
    COMMAND_CHANGES = "command_changes"  # Change of command ceremonies
    AWARD_PRESENTATIONS = "award_presentations"  # Military awards and decorations

@dataclass
class ExtractionSchema:
    """Defines how to extract data from a specific military article type"""
    article_type: MilitaryArticleType
    description: str
    fields: Dict[str, str]  # field_name -> description
    prompt_template: str
    example_output: Dict[str, Any]
    confidence_threshold: float = 0.7

# Define extraction schemas for different military article types
MILITARY_EXTRACTION_SCHEMAS = {
    MilitaryArticleType.OFFICIAL_ANNOUNCEMENTS: ExtractionSchema(
        article_type=MilitaryArticleType.OFFICIAL_ANNOUNCEMENTS,
        description="Official DoD and military service personnel announcements",
        fields={
            "name_rank": "Full name with rank/title (e.g., 'Colonel John Smith')",
            "name": "Full name without rank (e.g., 'John Smith')",
            "rank": "Current military rank (e.g., 'Colonel')",
            "promotion_grade": "New rank being promoted to",
            "new_assignment": "New position, command, or assignment",
            "current_assignment": "Current position or assignment",
            "previous_assignment": "Previous significant assignment if mentioned",
            "location": "Geographic location, base, or installation",
            "service_branch": "Military service (Army, Navy, Air Force, Marines, Space Force, Coast Guard)",
            "effective_date": "When the change takes effect",
            "announcement_type": "Type of change (promotion, assignment, retirement, etc.)",
            "unit_organization": "Specific unit, command, or organization",
            "years_of_service": "Total years of military service if mentioned",
            "education": "Military or civilian education mentioned",
            "awards_decorations": "Notable awards or decorations mentioned"
        },
        prompt_template="""
Extract US military personnel information from this official announcement.
Focus on promotions, assignments, retirements, and command changes.
Be precise with ranks, titles, and organizational structures.
""",
        example_output={
            "name_rank": "Colonel John A. Smith",
            "name": "John A. Smith",
            "rank": "Colonel",
            "promotion_grade": "Brigadier General",
            "new_assignment": "Commander, 1st Armored Brigade Combat Team",
            "current_assignment": "Deputy Chief of Staff, Operations",
            "previous_assignment": "Battalion Commander, 2nd Infantry Regiment",
            "location": "Fort Carson, Colorado",
            "service_branch": "Army",
            "effective_date": "January 15, 2025",
            "announcement_type": "promotion_and_assignment",
            "unit_organization": "4th Infantry Division",
            "years_of_service": "22 years",
            "education": "Master of Strategic Studies, Army War College",
            "awards_decorations": "Bronze Star Medal, Combat Action Badge"
        }
    ),
    
    MilitaryArticleType.NEWS_COVERAGE: ExtractionSchema(
        article_type=MilitaryArticleType.NEWS_COVERAGE,
        description="News articles covering military personnel changes",
        fields={
            "name_rank": "Full name with rank/title",
            "name": "Full name without rank",
            "rank": "Military rank",
            "promotion_grade": "New rank if promoted",
            "new_assignment": "New position or command",
            "current_assignment": "Current position",
            "location": "Geographic location or base",
            "service_branch": "Military service branch",
            "announcement_source": "Who announced the change (Pentagon, service secretary, etc.)",
            "effective_date": "When change takes effect",
            "change_type": "Type of personnel change",
            "news_context": "Additional context from news coverage",
            "quoted_officials": "Officials quoted in the article",
            "background_info": "Relevant background or career highlights",
            "strategic_significance": "Why this change is newsworthy"
        },
        prompt_template="""
Extract military personnel information from this news article.
Focus on official personnel changes covered by news media.
Include context about why the change is significant.
""",
        example_output={
            "name_rank": "Admiral Sarah Johnson",
            "name": "Sarah Johnson",
            "rank": "Admiral",
            "promotion_grade": "",
            "new_assignment": "Commander, U.S. Pacific Fleet",
            "current_assignment": "Deputy Chief of Naval Operations",
            "location": "Pearl Harbor, Hawaii",
            "service_branch": "Navy",
            "announcement_source": "Secretary of the Navy",
            "effective_date": "March 2025",
            "change_type": "major_command_assignment",
            "news_context": "First woman to command Pacific Fleet",
            "quoted_officials": "Secretary of Defense praised her extensive experience",
            "background_info": "30-year career, former carrier strike group commander",
            "strategic_significance": "Key appointment amid Pacific tensions"
        }
    ),

    MilitaryArticleType.COMMAND_CHANGES: ExtractionSchema(
        article_type=MilitaryArticleType.COMMAND_CHANGES,
        description="Change of command ceremonies and leadership transitions",
        fields={
            "outgoing_commander_name": "Name of departing commander",
            "outgoing_commander_rank": "Rank of departing commander",
            "incoming_commander_name": "Name of new commander",
            "incoming_commander_rank": "Rank of new commander",
            "command_unit": "Unit or organization changing command",
            "ceremony_location": "Where ceremony took place",
            "ceremony_date": "Date of change of command",
            "service_branch": "Military service branch",
            "outgoing_next_assignment": "Where outgoing commander is going",
            "incoming_previous_assignment": "Where incoming commander came from",
            "presiding_officer": "Senior official presiding over ceremony",
            "unit_mission": "Mission or role of the unit",
            "deployment_status": "Current deployment or operational status"
        },
        prompt_template="""
Extract information about military change of command ceremonies.
Focus on both outgoing and incoming commanders and their transitions.
""",
        example_output={
            "outgoing_commander_name": "Colonel Michael Davis",
            "outgoing_commander_rank": "Colonel",
            "incoming_commander_name": "Colonel Lisa Chen",
            "incoming_commander_rank": "Colonel",
            "command_unit": "15th Engineer Battalion",
            "ceremony_location": "Fort Leonard Wood, Missouri",
            "ceremony_date": "February 10, 2025",
            "service_branch": "Army",
            "outgoing_next_assignment": "Student, Army War College",
            "incoming_previous_assignment": "Executive Officer, 2nd Engineer Brigade",
            "presiding_officer": "Brigadier General Robert Taylor",
            "unit_mission": "Combat engineering support",
            "deployment_status": "Recently returned from deployment"
        }
    ),

    MilitaryArticleType.RETIREMENT_ANNOUNCEMENTS: ExtractionSchema(
        article_type=MilitaryArticleType.RETIREMENT_ANNOUNCEMENTS,
        description="Military retirement announcements and ceremonies",
        fields={
            "name_rank": "Full name with rank",
            "name": "Full name without rank",
            "rank": "Military rank",
            "service_branch": "Military service",
            "retirement_date": "Official retirement date",
            "years_of_service": "Total years of service",
            "final_assignment": "Last position held",
            "career_highlights": "Major assignments or achievements",
            "awards_decorations": "Notable awards and decorations",
            "retirement_ceremony": "Details about retirement ceremony",
            "post_retirement_plans": "Plans after military service",
            "family_info": "Spouse or family information if mentioned",
            "hometown": "Hometown or post-retirement location"
        },
        prompt_template="""
Extract information about military retirement announcements.
Focus on career summaries and service accomplishments.
""",
        example_output={
            "name_rank": "General Patricia Williams",
            "name": "Patricia Williams",
            "rank": "General",
            "service_branch": "Air Force",
            "retirement_date": "June 30, 2025",
            "years_of_service": "35 years",
            "final_assignment": "Commander, Air Mobility Command",
            "career_highlights": "First female pilot in squadron, former wing commander",
            "awards_decorations": "Distinguished Service Medal, Legion of Merit",
            "retirement_ceremony": "Scott Air Force Base ceremony",
            "post_retirement_plans": "Consulting for aerospace industry",
            "family_info": "Husband Colonel (ret.) Mark Williams",
            "hometown": "Returning to Denver, Colorado"
        }
    )
}

def get_schema_for_article_type(article_type: MilitaryArticleType) -> ExtractionSchema:
    """Get the extraction schema for a specific military article type"""
    return MILITARY_EXTRACTION_SCHEMAS.get(
        article_type, 
        MILITARY_EXTRACTION_SCHEMAS[MilitaryArticleType.OFFICIAL_ANNOUNCEMENTS]
    )

def detect_military_article_type(title: str, summary: str, content: str) -> MilitaryArticleType:
    """
    Automatically detect the type of military article based on content.
    Focused on US military personnel changes.
    """
    text = f"{title} {summary} {content}".lower()
    
    # Official announcement indicators
    official_indicators = [
        "announces", "announces the", "department of defense", "pentagon announces",
        "secretary of", "chief of staff", "service announces", "official announcement"
    ]
    
    # News coverage indicators
    news_indicators = [
        "reports", "according to", "sources say", "pentagon officials",
        "military officials", "defense officials", "reported that"
    ]
    
    # Command change indicators
    command_change_indicators = [
        "change of command", "assumes command", "relinquishes command",
        "takes command", "new commander", "command ceremony"
    ]
    
    # Retirement indicators
    retirement_indicators = [
        "retires", "retirement", "retiring", "ends career", "final assignment",
        "retirement ceremony", "years of service"
    ]
    
    # Score each type
    official_score = sum(1 for indicator in official_indicators if indicator in text)
    news_score = sum(1 for indicator in news_indicators if indicator in text)
    command_score = sum(1 for indicator in command_change_indicators if indicator in text)
    retirement_score = sum(1 for indicator in retirement_indicators if indicator in text)
    
    # Determine article type based on highest score
    if retirement_score >= 2:
        return MilitaryArticleType.RETIREMENT_ANNOUNCEMENTS
    elif command_score >= 2:
        return MilitaryArticleType.COMMAND_CHANGES
    elif news_score >= 2:
        return MilitaryArticleType.NEWS_COVERAGE
    elif official_score >= 1:
        return MilitaryArticleType.OFFICIAL_ANNOUNCEMENTS
    
    # Default to official announcements for military content
    return MilitaryArticleType.OFFICIAL_ANNOUNCEMENTS

def is_military_personnel_article(title: str, summary: str, content: str) -> bool:
    """
    Determine if an article is about US military personnel changes.
    Returns True only for relevant military personnel content.
    """
    text = f"{title} {summary} {content}".lower()
    
    # Must have military indicators
    military_keywords = [
        "general", "admiral", "colonel", "captain", "major", "lieutenant",
        "sergeant", "chief", "army", "navy", "air force", "marines", 
        "space force", "coast guard", "military", "pentagon", "defense",
        "command", "promotion", "assignment", "retirement"
    ]
    
    # Must have personnel change indicators
    personnel_keywords = [
        "promotion", "promoted", "assignment", "assigned", "command",
        "appointment", "appointed", "nomination", "nominated", "retirement",
        "retires", "assumes", "relinquishes", "new", "change"
    ]
    
    # Exclude non-personnel topics
    exclude_keywords = [
        "equipment", "weapons", "budget", "contract", "exercise",
        "training", "deployment", "operation", "mission", "policy",
        "strategy", "base closure", "facility"
    ]
    
    military_score = sum(1 for keyword in military_keywords if keyword in text)
    personnel_score = sum(1 for keyword in personnel_keywords if keyword in text)
    exclude_score = sum(1 for keyword in exclude_keywords if keyword in text)
    
    # Must have military terms AND personnel terms, with minimal exclusions
    return military_score >= 2 and personnel_score >= 1 and exclude_score <= 2