"""Test Pydantic models for data validation"""
import pytest
from ventureai.backend.models import (
    StartupProfile, MarketAnalysis, FounderAnalysis,
    FinancialAnalysis, BearCase, InvestmentMemo
)


class TestStartupProfile:
    def test_valid_profile(self):
        profile = StartupProfile(company_name="Airbnb")
        assert profile.company_name == "Airbnb"
        assert profile.score == 0
        assert profile.founders == []

    def test_score_bounds(self):
        # Valid: 0-100
        profile = StartupProfile(company_name="Test", score=50)
        assert profile.score == 50

    def test_score_validation_fails_over_100(self):
        # Should reject score > 100
        with pytest.raises(ValueError):
            StartupProfile(company_name="Test", score=101)

    def test_score_validation_fails_negative(self):
        # Should reject score < 0
        with pytest.raises(ValueError):
            StartupProfile(company_name="Test", score=-1)

    def test_with_all_fields(self):
        profile = StartupProfile(
            company_name="Airbnb",
            one_liner="Rent out your space",
            stage="Early Stage",
            industry="Travel Tech",
            founders=["Brian Chesky", "Joe Gebbia"],
            location="San Francisco",
            website="airbnb.com",
            score=85
        )
        assert profile.founders == ["Brian Chesky", "Joe Gebbia"]
        assert profile.score == 85


class TestInvestmentMemo:
    def test_valid_verdict_invest(self):
        memo = InvestmentMemo(
            verdict="INVEST",
            confidence_score=80
        )
        assert memo.verdict == "INVEST"

    def test_valid_verdict_pass(self):
        memo = InvestmentMemo(verdict="PASS")
        assert memo.verdict == "PASS"

    def test_valid_verdict_watch(self):
        memo = InvestmentMemo(verdict="WATCH")
        assert memo.verdict == "WATCH"

    def test_invalid_verdict(self):
        # Should reject invalid verdict
        with pytest.raises(ValueError):
            InvestmentMemo(verdict="REJECT")

    def test_score_bounds(self):
        memo = InvestmentMemo(
            verdict="INVEST",
            confidence_score=100,
            market_score=75,
            founder_score=90,
            financial_score=60,
            bear_case_score=40
        )
        assert memo.confidence_score == 100
        assert memo.market_score == 75

    def test_overall_score_clamping(self):
        # Overall score > 100 should be clamped to 100
        memo = InvestmentMemo(
            verdict="INVEST",
            overall_score=150
        )
        assert memo.overall_score == 100

    def test_overall_score_clamp_negative(self):
        # Overall score < 0 should be clamped to 0
        memo = InvestmentMemo(
            verdict="INVEST",
            overall_score=-10
        )
        assert memo.overall_score == 0


class TestMarketAnalysis:
    def test_valid_market_analysis(self):
        market = MarketAnalysis(
            tam="$50B",
            market_growth="30% CAGR",
            timing_verdict="Perfect timing",
            competitors=["Vrbo", "HomeAway"],
            market_score=80
        )
        assert market.market_score == 80
        assert market.competitors == ["Vrbo", "HomeAway"]

    def test_market_score_bounds(self):
        market = MarketAnalysis(market_score=50)
        assert market.market_score == 50


class TestFounderAnalysis:
    def test_founder_analysis_with_prior_exits(self):
        founder = FounderAnalysis(
            founders=[{"name": "Brian Chesky", "background": "Design"}],
            prior_exits=True,
            founder_score=90
        )
        assert founder.prior_exits is True
        assert founder.founder_score == 90

    def test_founder_analysis_first_time(self):
        founder = FounderAnalysis(
            founders=[{"name": "First Timer"}],
            prior_exits=False,
            founder_score=40
        )
        assert founder.prior_exits is False


class TestFinancialAnalysis:
    def test_financial_analysis_with_red_flags(self):
        financial = FinancialAnalysis(
            revenue_model="Marketplace SaaS",
            raise_amount="$5M",
            red_flags=["High burn rate", "Negative unit economics"],
            financial_score=35
        )
        assert len(financial.red_flags) == 2
        assert financial.financial_score == 35

    def test_financial_analysis_clean(self):
        financial = FinancialAnalysis(
            revenue_model="Recurring subscription",
            red_flags=[],
            financial_score=85
        )
        assert len(financial.red_flags) == 0


class TestBearCase:
    def test_bear_case_challenges(self):
        bear = BearCase(
            market_challenges=["Competition", "Regulation"],
            founder_challenges=["No ops experience"],
            financial_challenges=["Negative unit economics"],
            failure_modes=["Market pivot required"],
            bear_case_score=65
        )
        assert len(bear.market_challenges) == 2
        assert bear.bear_case_score == 65
