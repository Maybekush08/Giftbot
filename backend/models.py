from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class GiftProfile(BaseModel):
    recipient: Optional[str] = Field(None, description="Who the gift is for (e.g., 'my sister')")
    age: Optional[str] = Field(None, description="Age or age range (e.g., '29', '30s')")
    relationship: Optional[str] = Field(None, description="Relationship to giver (e.g., friend, partner, coworker)")
    personality: Optional[str] = Field(None, description="Traits like minimalist, sentimental, practical, playful")
    occasion: Optional[str] = Field(None, description="Birthday, Christmas, graduation, housewarming, etc")
    budget_usd: Optional[float] = Field(None, description="Budget in USD")
    no_go: Optional[str] = Field(None, description="No-go ideas (e.g., 'no perfumes, no alcohol')")
    interests: Optional[str] = Field(None, description="Hobbies/interests")
    location_us: Optional[str] = Field(None, description="US location context if relevant")
    extra_notes: Optional[str] = Field(None, description="Anything else")


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str = ""
    source: Literal["tavily", "duckduckgo"]


class GiftIdea(BaseModel):
    name: str
    why_it_fits: str
    estimated_price: Optional[str] = None
    buy_link: Optional[str] = None
    score: float = 0.0
    evidence_urls: List[str] = Field(default_factory=list)


class GiftBatch(BaseModel):
    ideas: List[GiftIdea]
    search_notes: str = ""
