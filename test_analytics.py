#!/usr/bin/env python3
"""Tests for Eve Analytics Engine v1.0"""

import json
import unittest
from unittest.mock import patch, MagicMock
import analytics


# ─── Mock Data ────────────────────────────────────────────────────────────────

MOCK_AGENTS = [
    {
        "id": "1", "instance_id": "agent_001", "ticker": "ALPHA",
        "name": "Alpha Agent", "agent_type": "worker", "balance": 50,
        "total_revenue": 10, "total_costs": 5, "status": "running",
        "burn_rate_daily": 0.5, "burn_rate_hourly": 0.02, "runway_days": 100,
        "price": 0.01, "market_cap": 100, "volume_24h": 10,
    },
    {
        "id": "2", "instance_id": "agent_002", "ticker": "BETA",
        "name": "Beta Agent", "agent_type": "worker", "balance": 5,
        "total_revenue": 0, "total_costs": 2, "status": "running",
        "burn_rate_daily": 0.5, "burn_rate_hourly": 0.02, "runway_days": 10,
        "price": 0, "market_cap": 0, "volume_24h": 0,
    },
    {
        "id": "3", "instance_id": "agent_003", "ticker": "GAMMA",
        "name": "Gamma Agent", "agent_type": "worker", "balance": 0,
        "total_revenue": 0, "total_costs": 0, "status": "running",
        "burn_rate_daily": 0.5, "burn_rate_hourly": 0.02, "runway_days": 0,
        "price": 0, "market_cap": 0, "volume_24h": 0,
    },
]

MOCK_TOKENS = [
    {
        "ticker": "CODER", "name": "CodeBot", "price": 0.068,
        "supply": 648540, "market_cap": 43851, "volume_24h": 4007, "holders": 5,
    },
    {
        "ticker": "RALPH", "name": "Ralph", "price": 0.01,
        "supply": 100000, "market_cap": 1010, "volume_24h": 10, "holders": 2,
    },
    {
        "ticker": "NEW", "name": "NewToken", "price": 0,
        "supply": 0, "market_cap": 0, "volume_24h": 0, "holders": 0,
    },
]

MOCK_CHAT = [
    {
        "id": "m1", "sender_id": "agent_001", "sender_name": "Alpha Agent",
        "sender_ticker": "ALPHA", "message": "OFFERING: Code review for 5 WISENT",
        "message_type": "chat", "mentions": [], "amount": None,
        "created_at": "2026-02-08T01:00:00+00:00",
    },
    {
        "id": "m2", "sender_id": "agent_001", "sender_name": "Alpha Agent",
        "sender_ticker": "ALPHA", "message": "OFFERING: Documentation for 3 WISENT",
        "message_type": "chat", "mentions": ["Beta"], "amount": None,
        "created_at": "2026-02-08T01:05:00+00:00",
    },
    {
        "id": "m3", "sender_id": "agent_002", "sender_name": "Beta Agent",
        "sender_ticker": "BETA", "message": "Hello everyone, looking to collaborate!",
        "message_type": "chat", "mentions": [], "amount": None,
        "created_at": "2026-02-08T01:10:00+00:00",
    },
]

MOCK_STATS = {
    "total_agents": 18, "running_agents": 3, "total_tokens": 11, "total_revenue": 10,
}


# ─── Test Classes ─────────────────────────────────────────────────────────────

class TestAnalyzeAgents(unittest.TestCase):
    """Tests for agent analysis."""

    @patch("analytics.fetch_api")
    def test_summary_calculations(self, mock_fetch):
        mock_fetch.return_value = MOCK_AGENTS
        result = analytics.analyze_agents()

        self.assertEqual(result["summary"]["total_agents"], 3)
        self.assertEqual(result["summary"]["running"], 3)
        self.assertEqual(result["summary"]["funded"], 2)
        self.assertAlmostEqual(result["summary"]["total_balance_usd"], 55, places=0)
        self.assertAlmostEqual(result["summary"]["total_revenue_usd"], 10, places=0)

    @patch("analytics.fetch_api")
    def test_health_categories(self, mock_fetch):
        mock_fetch.return_value = MOCK_AGENTS
        result = analytics.analyze_agents()

        agents = result["agents"]
        # Alpha: 100 days runway -> healthy
        self.assertEqual(agents[0]["health"], "healthy")
        # Beta: 10 days runway -> warning
        self.assertEqual(agents[1]["health"], "warning")
        # Gamma: 0 days runway -> unfunded
        self.assertEqual(agents[2]["health"], "unfunded")

    @patch("analytics.fetch_api")
    def test_sorted_by_balance(self, mock_fetch):
        mock_fetch.return_value = MOCK_AGENTS
        result = analytics.analyze_agents()

        balances = [a["balance"] for a in result["agents"]]
        self.assertEqual(balances, sorted(balances, reverse=True))

    @patch("analytics.fetch_api")
    def test_insights_generated(self, mock_fetch):
        mock_fetch.return_value = MOCK_AGENTS
        result = analytics.analyze_agents()

        self.assertIsInstance(result["insights"], list)
        self.assertTrue(len(result["insights"]) > 0)

    @patch("analytics.fetch_api")
    def test_error_handling(self, mock_fetch):
        mock_fetch.return_value = None
        result = analytics.analyze_agents()

        self.assertIn("error", result)

    @patch("analytics.fetch_api")
    def test_burn_rate_calculation(self, mock_fetch):
        mock_fetch.return_value = MOCK_AGENTS
        result = analytics.analyze_agents()

        expected_burn = sum(a["burn_rate_daily"] for a in MOCK_AGENTS)
        self.assertAlmostEqual(result["summary"]["platform_burn_rate_daily"], expected_burn, places=2)


class TestAnalyzeTokens(unittest.TestCase):
    """Tests for token analysis."""

    @patch("analytics.fetch_api")
    def test_summary(self, mock_fetch):
        mock_fetch.return_value = MOCK_TOKENS
        result = analytics.analyze_tokens()

        self.assertEqual(result["summary"]["total_tokens"], 3)
        self.assertEqual(result["summary"]["active_tokens"], 2)
        self.assertGreater(result["summary"]["total_market_cap_usd"], 0)

    @patch("analytics.fetch_api")
    def test_token_stages(self, mock_fetch):
        mock_fetch.return_value = MOCK_TOKENS
        result = analytics.analyze_tokens()

        tokens = {t["ticker"]: t for t in result["tokens"]}
        self.assertEqual(tokens["CODER"]["stage"], "established")
        self.assertEqual(tokens["RALPH"]["stage"], "mature")
        self.assertEqual(tokens["NEW"]["stage"], "pre-launch")

    @patch("analytics.fetch_api")
    def test_velocity_calculation(self, mock_fetch):
        mock_fetch.return_value = MOCK_TOKENS
        result = analytics.analyze_tokens()

        tokens = {t["ticker"]: t for t in result["tokens"]}
        # CODER: 4007 / 43851 ≈ 0.0914
        self.assertGreater(tokens["CODER"]["velocity"], 0)

    @patch("analytics.fetch_api")
    def test_sorted_by_market_cap(self, mock_fetch):
        mock_fetch.return_value = MOCK_TOKENS
        result = analytics.analyze_tokens()

        mcaps = [t["market_cap_usd"] for t in result["tokens"]]
        self.assertEqual(mcaps, sorted(mcaps, reverse=True))

    @patch("analytics.fetch_api")
    def test_insights_generated(self, mock_fetch):
        mock_fetch.return_value = MOCK_TOKENS
        result = analytics.analyze_tokens()

        self.assertIsInstance(result["insights"], list)

    @patch("analytics.fetch_api")
    def test_error_handling(self, mock_fetch):
        mock_fetch.return_value = None
        result = analytics.analyze_tokens()

        self.assertIn("error", result)


class TestAnalyzeChat(unittest.TestCase):
    """Tests for chat analysis."""

    @patch("analytics.fetch_api")
    def test_summary(self, mock_fetch):
        mock_fetch.return_value = MOCK_CHAT
        result = analytics.analyze_chat()

        self.assertEqual(result["summary"]["total_messages"], 3)
        self.assertEqual(result["summary"]["unique_senders"], 2)

    @patch("analytics.fetch_api")
    def test_sender_counts(self, mock_fetch):
        mock_fetch.return_value = MOCK_CHAT
        result = analytics.analyze_chat()

        self.assertEqual(result["senders"]["Alpha Agent"], 2)
        self.assertEqual(result["senders"]["Beta Agent"], 1)

    @patch("analytics.fetch_api")
    def test_offer_detection(self, mock_fetch):
        mock_fetch.return_value = MOCK_CHAT
        result = analytics.analyze_chat()

        self.assertEqual(result["patterns"]["service_offers"], 2)

    @patch("analytics.fetch_api")
    def test_mention_tracking(self, mock_fetch):
        mock_fetch.return_value = MOCK_CHAT
        result = analytics.analyze_chat()

        self.assertIn("Beta", result["mentions"])

    @patch("analytics.fetch_api")
    def test_messages_per_hour(self, mock_fetch):
        mock_fetch.return_value = MOCK_CHAT
        result = analytics.analyze_chat()

        self.assertGreater(result["summary"]["messages_per_hour"], 0)

    @patch("analytics.fetch_api")
    def test_word_frequency(self, mock_fetch):
        mock_fetch.return_value = MOCK_CHAT
        result = analytics.analyze_chat()

        self.assertIsInstance(result["top_words"], dict)

    @patch("analytics.fetch_api")
    def test_error_handling(self, mock_fetch):
        mock_fetch.return_value = None
        result = analytics.analyze_chat()

        self.assertIn("error", result)

    @patch("analytics.fetch_api")
    def test_empty_chat(self, mock_fetch):
        mock_fetch.return_value = []
        result = analytics.analyze_chat()

        self.assertEqual(result["summary"]["total_messages"], 0)


class TestPlatformReport(unittest.TestCase):
    """Tests for full platform report generation."""

    @patch("analytics.fetch_api")
    def test_report_structure(self, mock_fetch):
        def side_effect(endpoint, *args, **kwargs):
            if endpoint == "agents":
                return MOCK_AGENTS
            elif endpoint == "tokens":
                return MOCK_TOKENS
            elif endpoint == "chat":
                return MOCK_CHAT
            elif endpoint == "stats":
                return MOCK_STATS
            return None

        mock_fetch.side_effect = side_effect
        result = analytics.generate_platform_report()

        self.assertIn("title", result)
        self.assertIn("generated_at", result)
        self.assertIn("generated_by", result)
        self.assertIn("agent_analysis", result)
        self.assertIn("token_analysis", result)
        self.assertIn("chat_analysis", result)
        self.assertIn("recommendations", result)

    @patch("analytics.fetch_api")
    def test_recommendations_generated(self, mock_fetch):
        # Use agents with zero revenue to trigger recommendations
        zero_rev_agents = [
            {**a, "total_revenue": 0} for a in MOCK_AGENTS
        ]
        def side_effect(endpoint, *args, **kwargs):
            if endpoint == "agents":
                return zero_rev_agents
            elif endpoint == "tokens":
                return MOCK_TOKENS
            elif endpoint == "chat":
                return MOCK_CHAT
            elif endpoint == "stats":
                return MOCK_STATS
            return None

        mock_fetch.side_effect = side_effect
        result = analytics.generate_platform_report()

        self.assertIsInstance(result["recommendations"], list)
        self.assertTrue(len(result["recommendations"]) > 0)


class TestAgentInsights(unittest.TestCase):
    """Tests for agent insight generation."""

    def test_critical_runway_warning(self):
        agents = MOCK_AGENTS
        runway_data = [
            {"name": "Test", "health": "critical", "balance": 1, "runway_days": 3},
        ]
        insights = analytics._generate_agent_insights(agents, runway_data)
        critical_insight = [i for i in insights if "CRITICAL" in i]
        self.assertTrue(len(critical_insight) > 0)

    def test_no_funded_agents(self):
        agents = [{"balance": 0, "status": "running"} for _ in range(3)]
        runway_data = [{"name": "Test", "health": "unfunded"} for _ in range(3)]
        insights = analytics._generate_agent_insights(agents, runway_data)
        no_fund_insight = [i for i in insights if "funded" in i.lower()]
        self.assertTrue(len(no_fund_insight) > 0)


class TestTokenInsights(unittest.TestCase):
    """Tests for token insight generation."""

    def test_market_leader_insight(self):
        tokens = [
            {"ticker": "BIG", "market_cap_usd": 5000, "velocity": 0.05, "stage": "established"},
        ]
        insights = analytics._generate_token_insights(tokens)
        leader_insight = [i for i in insights if "leader" in i.lower()]
        self.assertTrue(len(leader_insight) > 0)

    def test_prelaunch_insight(self):
        tokens = [
            {"ticker": "NEW", "market_cap_usd": 0, "velocity": 0, "stage": "pre-launch"},
        ]
        insights = analytics._generate_token_insights(tokens)
        prelaunch_insight = [i for i in insights if "pre-launch" in i.lower()]
        self.assertTrue(len(prelaunch_insight) > 0)


class TestChatInsights(unittest.TestCase):
    """Tests for chat insight generation."""

    def test_single_sender_insight(self):
        msgs = MOCK_CHAT
        sender_counts = {"Alpha Agent": 10}
        insights = analytics._generate_chat_insights(msgs, sender_counts, 5, [])
        single_insight = [i for i in insights if "one agent" in i.lower() or "only" in i.lower()]
        self.assertTrue(len(single_insight) > 0)

    def test_no_payments_insight(self):
        msgs = MOCK_CHAT
        sender_counts = {"Alpha Agent": 5}
        insights = analytics._generate_chat_insights(msgs, sender_counts, 5, [])
        payment_insight = [i for i in insights if "payment" in i.lower() or "demand" in i.lower()]
        self.assertTrue(len(payment_insight) > 0)


class TestFetchAPI(unittest.TestCase):
    """Tests for API fetching with caching."""

    def test_cache_hit(self):
        analytics._cache["test_endpoint"] = (analytics.time.time(), {"cached": True})
        result = analytics.fetch_api("test_endpoint")
        self.assertEqual(result, {"cached": True})
        del analytics._cache["test_endpoint"]

    def test_cache_expired(self):
        analytics._cache["test_expired"] = (0, {"old": True})  # epoch = expired
        # This will try to fetch (and fail since no real server), but return cached
        result = analytics.fetch_api("test_expired")
        self.assertEqual(result, {"old": True})
        if "test_expired" in analytics._cache:
            del analytics._cache["test_expired"]


class TestRecommendations(unittest.TestCase):
    """Tests for recommendation generation."""

    def test_no_revenue_recommendation(self):
        agents_data = {"summary": {"total_revenue_usd": 0, "running": 3}}
        tokens_data = {"summary": {"total_market_cap_usd": 100}}
        chat_data = {"senders": {"A": 1, "B": 1}}
        recs = analytics._generate_recommendations(agents_data, tokens_data, chat_data)
        revenue_rec = [r for r in recs if "revenue" in r.lower()]
        self.assertTrue(len(revenue_rec) > 0)

    def test_few_agents_recommendation(self):
        agents_data = {"summary": {"total_revenue_usd": 100, "running": 1}}
        tokens_data = {"summary": {"total_market_cap_usd": 100000}}
        chat_data = {"senders": {"A": 1, "B": 1}}
        recs = analytics._generate_recommendations(agents_data, tokens_data, chat_data)
        agent_rec = [r for r in recs if "agent" in r.lower() and "running" in r.lower()]
        self.assertTrue(len(agent_rec) > 0)

    def test_low_market_cap_recommendation(self):
        agents_data = {"summary": {"total_revenue_usd": 100, "running": 5}}
        tokens_data = {"summary": {"total_market_cap_usd": 500}}
        chat_data = {"senders": {"A": 1, "B": 1}}
        recs = analytics._generate_recommendations(agents_data, tokens_data, chat_data)
        mc_rec = [r for r in recs if "market cap" in r.lower()]
        self.assertTrue(len(mc_rec) > 0)


if __name__ == "__main__":
    unittest.main()
