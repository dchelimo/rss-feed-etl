"""
Enhanced data models for universal news article extraction.
Supports dynamic schemas and multiple article types.
"""

from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, 
    Float, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime
from models.orm_models import Base

class ArticleType(Base):
    """Article type classification"""
    __tablename__ = 'article_types'
    
    id = Column(Integer, primary_key=True)
    type_name = Column(String(50), unique=True, nullable=False)  # e.g., 'business_news'
    description = Column(Text)
    schema_version = Column(String(20), default='1.0')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    extractions = relationship("UniversalExtraction", back_populates="article_type_ref")

class UniversalExtraction(Base):
    """Universal extraction results for any article type"""
    __tablename__ = 'universal_extractions'
    
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=False)
    article_type_id = Column(Integer, ForeignKey('article_types.id'))
    
    # Extraction metadata
    extraction_confidence = Column(Float, default=0.0)
    schema_used = Column(String(100))
    model_used = Column(String(50), default='claude-sonnet-4')
    processing_time = Column(Float)  # seconds
    
    # Raw extraction data (JSON)
    raw_extraction_data = Column(JSON)  # Full Claude response
    processed_entities = Column(JSON)   # Cleaned/validated entities
    
    # Status and timestamps
    status = Column(String(20), default='completed')  # completed, failed, pending
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    article = relationship("Article")
    article_type_ref = relationship("ArticleType", back_populates="extractions")
    entities = relationship("ExtractedEntity", back_populates="extraction")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_extraction_article_type', 'article_id', 'article_type_id'),
        Index('idx_extraction_confidence', 'extraction_confidence'),
        Index('idx_extraction_status', 'status'),
    )

class ExtractedEntity(Base):
    """Individual entities extracted from articles (people, companies, events, etc.)"""
    __tablename__ = 'extracted_entities'
    
    id = Column(Integer, primary_key=True)
    extraction_id = Column(Integer, ForeignKey('universal_extractions.id'), nullable=False)
    
    # Entity identification
    entity_type = Column(String(50))  # person, company, event, location, etc.
    entity_name = Column(String(200))  # primary identifier
    
    # Dynamic entity data (JSON for flexibility)
    entity_data = Column(JSON)  # All extracted fields for this entity
    
    # Confidence and validation
    entity_confidence = Column(Float, default=0.0)
    validation_status = Column(String(20), default='unvalidated')  # validated, rejected, unvalidated
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships  
    extraction = relationship("UniversalExtraction", back_populates="entities")
    
    # Indexes
    __table_args__ = (
        Index('idx_entity_name_type', 'entity_name', 'entity_type'),
        Index('idx_entity_confidence', 'entity_confidence'),
    )

class EntityRelationship(Base):
    """Relationships between extracted entities"""
    __tablename__ = 'entity_relationships'
    
    id = Column(Integer, primary_key=True)
    source_entity_id = Column(Integer, ForeignKey('extracted_entities.id'))
    target_entity_id = Column(Integer, ForeignKey('extracted_entities.id'))
    relationship_type = Column(String(50))  # works_for, promoted_to, acquired_by, etc.
    confidence = Column(Float, default=0.0)
    metadata = Column(JSON)  # Additional relationship context
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    source_entity = relationship("ExtractedEntity", foreign_keys=[source_entity_id])
    target_entity = relationship("ExtractedEntity", foreign_keys=[target_entity_id])

class ExtractionTemplate(Base):
    """Reusable extraction templates/schemas"""
    __tablename__ = 'extraction_templates'
    
    id = Column(Integer, primary_key=True)
    template_name = Column(String(100), unique=True, nullable=False)
    article_type = Column(String(50))
    description = Column(Text)
    
    # Template definition
    field_schema = Column(JSON)      # Field definitions
    prompt_template = Column(Text)   # Claude prompt template
    example_output = Column(JSON)    # Example extraction
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100))
    
    # Quality metrics
    avg_confidence = Column(Float, default=0.0)
    success_rate = Column(Float, default=0.0)

# Enhanced view for easy querying
class EnhancedFlatRow(Base):
    """Enhanced flat view combining article and extraction data"""
    __tablename__ = 'enhanced_flat_rows'
    
    id = Column(Integer, primary_key=True)
    
    # Article information
    article_id = Column(Integer, ForeignKey('articles.id'))
    announcement_title = Column(Text)
    date_published = Column(DateTime)
    summary = Column(Text)
    link = Column(Text)
    feed_name = Column(String(200))
    
    # Extraction metadata
    article_type = Column(String(50))
    extraction_confidence = Column(Float)
    entity_count = Column(Integer, default=0)
    
    # Primary entity data (for backward compatibility)
    primary_entity_name = Column(String(200))
    primary_entity_type = Column(String(50))
    primary_entity_data = Column(JSON)
    
    # All entities (JSON array)
    all_entities = Column(JSON)
    
    # Processing metadata
    processing_status = Column(String(20), default='completed')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    article = relationship("Article")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_flat_article_type', 'article_type'),
        Index('idx_flat_confidence', 'extraction_confidence'),
        Index('idx_flat_date', 'date_published'),
        Index('idx_flat_entity_name', 'primary_entity_name'),
    )

# Migration function to populate article types
def populate_article_types(session):
    """Populate the article_types table with predefined types"""
    from config.extraction_schemas import EXTRACTION_SCHEMAS
    
    for article_type, schema in EXTRACTION_SCHEMAS.items():
        existing = session.query(ArticleType).filter_by(
            type_name=article_type.value
        ).first()
        
        if not existing:
            new_type = ArticleType(
                type_name=article_type.value,
                description=schema.description,
                schema_version='1.0'
            )
            session.add(new_type)
    
    session.commit()