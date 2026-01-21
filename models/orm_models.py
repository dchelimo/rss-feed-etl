from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class Feed(Base):
	__tablename__ = 'feeds'
	id = Column(Integer, primary_key=True)
	name = Column(String, unique=True)
	url = Column(Text, nullable=False)
	articles = relationship("Article", back_populates="feed")

class Article(Base):
	__tablename__ = 'articles'
	id = Column(Integer, primary_key=True)
	feed_id = Column(Integer, ForeignKey('feeds.id'))
	title = Column(Text)
	link = Column(Text, unique=True)
	published = Column(DateTime)
	summary = Column(Text)
	inserted_at = Column(DateTime, default=datetime.utcnow)
	feed = relationship("Feed", back_populates="articles")
	body = relationship("ArticleBody", uselist=False, back_populates="article")
	extracted_fields = relationship("ExtractedField", back_populates="article")

class ArticleBody(Base):
	__tablename__ = 'article_bodies'
	id = Column(Integer, primary_key=True)
	article_id = Column(Integer, ForeignKey('articles.id'), unique=True)
	body_text = Column(Text)
	article = relationship("Article", back_populates="body")


class ExtractedField(Base):
	__tablename__ = 'extracted_fields'
	id = Column(Integer, primary_key=True)
	article_id = Column(Integer, ForeignKey('articles.id'))
	field_name = Column(String)
	field_value = Column(Text)
	article = relationship("Article", back_populates="extracted_fields")
	__table_args__ = (UniqueConstraint('article_id', 'field_name'),)

# --- FLATTENED NOMINATION ROWS TABLE ---

# --- FLATTENED NOMINATION ROWS TABLE ---
class FlatRow(Base):
	__tablename__ = 'flat_rows'
	__table_args__ = (
		UniqueConstraint('announcement_title', 'name_rank', name='flat_rows_unique'),
	)
	id = Column(Integer, primary_key=True)
	announcement_title = Column(Text)
	date_published = Column(DateTime)
	summary = Column(Text)
	link = Column(Text)
	name_rank = Column(Text)
	name = Column(Text)
	rank = Column(Text)
	location = Column(Text)
	new_assignment = Column(Text)
	promotion_grade = Column(Text)
	current_assignment = Column(Text)
	inserted_at = Column(DateTime, default=datetime.utcnow)
