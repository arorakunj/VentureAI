from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator


class StartupProfile(BaseModel):
    company_name: str
    one_liner: Optional[str] = None
    stage: Optional[str] = None
    industry: Optional[str] = None
    founders: List[str] = Field(default_factory=list)
    funding_history: List[Dict[str, Any]] = Field(default_factory=list)
    location: Optional[str] = None
    website: Optional[str] = None
    raw_description: Optional[str] = None
    score: int = Field(0, ge=0, le=100)
    summary: Optional[str] = None

    class Config:
        from_attributes = True


class MarketAnalysis(BaseModel):
    tam: Optional[str] = None
    market_growth: Optional[str] = None
    timing_verdict: Optional[str] = None
    competitors: List[str] = Field(default_factory=list)
    differentiation: Optional[str] = None
    market_score: int = Field(0, ge=0, le=100)
    key_risks: List[str] = Field(default_factory=list)
    summary: Optional[str] = None

    class Config:
        from_attributes = True


class FounderAnalysis(BaseModel):
    founders: List[Dict[str, Any]] = Field(default_factory=list)
    team_completeness: Optional[str] = None
    prior_exits: bool = False
    founder_score: int = Field(0, ge=0, le=100)
    summary: Optional[str] = None

    class Config:
        from_attributes = True


class FinancialAnalysis(BaseModel):
    revenue_model: Optional[str] = None
    unit_economics: Optional[Dict[str, Any]] = Field(default_factory=dict)
    raise_amount: Optional[str] = None
    burn_assessment: Optional[str] = None
    path_to_profitability: Optional[str] = None
    financial_score: int = Field(0, ge=0, le=100)
    red_flags: List[str] = Field(default_factory=list)
    summary: Optional[str] = None

    class Config:
        from_attributes = True


class BearCase(BaseModel):
    market_challenges: List[str] = Field(default_factory=list)
    founder_challenges: List[str] = Field(default_factory=list)
    financial_challenges: List[str] = Field(default_factory=list)
    failure_modes: List[str] = Field(default_factory=list)
    bear_case_score: int = Field(0, ge=0, le=100)
    summary: Optional[str] = None

    class Config:
        from_attributes = True


class InvestmentMemo(BaseModel):
    verdict: Literal['PASS', 'INVEST', 'WATCH']
    confidence_score: int = Field(0, ge=0, le=100)
    executive_summary: Optional[str] = None
    market_score: int = Field(0, ge=0, le=100)
    founder_score: int = Field(0, ge=0, le=100)
    financial_score: int = Field(0, ge=0, le=100)
    bear_case_score: int = Field(0, ge=0, le=100)
    overall_score: int = Field(0, ge=0)
    recommendation: Optional[str] = None
    due_diligence_questions: List[str] = Field(default_factory=list)
    suggested_valuation_range: Optional[str] = None
    summary: Optional[str] = None

    @validator('overall_score')
    def overall_within_bounds(cls, v):
        if v is None:
            return 0
        return max(0, min(100, v))

    class Config:
        from_attributes = True
