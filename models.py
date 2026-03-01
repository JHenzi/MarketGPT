from pydantic import BaseModel, Field
from typing import Literal, Dict

class MarketSignal(BaseModel):
    ticker: str = Field(..., description="Upper case ticker symbol, e.g., 'AAPL'")
    company_name: str = Field(..., description="The full name of the company")
    signal_type: Literal["Headwind", "Tailwind"] = Field(..., description="The type of financial signal")
    summary: str = Field(..., description="Short description of the event")
    impact_score: float = Field(..., ge=-1.0, le=1.0, description="Impact score from -1.0 to 1.0")
    source_info: Dict[str, str] = Field(..., description="Dictionary containing 'url' and 'title'")
