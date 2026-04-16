from typing import TypedDict, List
from pydantic import BaseModel, Field

class StoryAngle(BaseModel):
    headline: str = Field(description="The proposed headline for the story angle.")
    rationale: str = Field(description="Strategic explanation with specific date/source reference.")
    outlet_specific: str = Field(description="The specific target publication (e.g., Electrek, The Verge).")
    outlet_category: str = Field(description="Category of the outlet (trade_press, consumer_tech, etc.).")
    why_now: str = Field(description="The timeliness factor for this angle.")
    source_urls: List[str] = Field(description="List of URLs from the raw news that inspired this angle.", default=[])

class AgentState(TypedDict):
    query: str
    raw_news: List[dict]
    competitor_mentions: List[str]
    generated_angles: List[StoryAngle]
    feedback: str
    iteration: int

class StoryAngles(BaseModel):
    angles: List[StoryAngle] = Field(description="List of strategic PR story angles.")
