from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class KeywordItem(BaseModel):
    word: str
    score: float
    importance: str

class DifficultyWord(BaseModel):
    word: str
    definition: str
    level: int

class ProcessResponse(BaseModel):
    id: str  # UUID
    original_text: str
    highlighted_html: str
    highlighted_markdown: str
    keywords: List[KeywordItem]
    difficult_words: List[DifficultyWord]
    summary: str
    processing_time: float
    created_at: datetime

class DocumentListItem(BaseModel):
    id: str
    title: Optional[str]
    summary: str
    created_at: datetime