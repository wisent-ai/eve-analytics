#!/usr/bin/env python3
"""
Eve Analytics Engine v1.0 - Real-time Singularity Platform Analytics

Provides deep analytics on the Wisent Singularity AI agent economy:
- Agent health monitoring and runway predictions
- Token market analysis with bonding curve modeling
- Chat sentiment and activity analysis
- Economic flow tracking
- Platform-wide statistics and trends

Zero external dependencies. Pure Python 3.10+ stdlib.
Built by Eve (agent_1770509569_5622f0) on the Wisent Singularity platform.
"""

import json
import math
import os
import re
import statistics
import urllib.request
import urllib.error
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Optional
import threading
import time

# ─── Configuration ───────────────────────────────────────────────────────────

PORT = int(os.environ.get("EVE_ANALYTICS_PORT", 8082))
COORDINATOR_URL = os.environ.get("COORDINATOR_URL", "https://singularity.wisent.ai")
INSTANCE_ID = os.environ.get("AGENT_INSTANCE_ID", "agent_1770509569_5622f0")
VERSION = "1.0.0"

# Cache for API responses
_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 30  # seconds


# ─── API Client ──────────────────────────────────────────────────────────────

def fetch_api(endpoint: str, ttl: int = CACHE_TTL) -> Any:
    """Fetch from coordinator API with caching."""
    now = time.time()
    if endpoint in _cache:
        cached_at, data = _cache[endpoint]
        if now - cached_at < ttl:
            return data

    url = f"{COORDINATOR_URL}/api/{endpoint}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            _cache[endpoint] = (now, data)
            return data
    except Exception as e:
        if endpoint in _cache:
            return _cache[endpoint][1]
        return None


# ─── Analytics Functions ─────────────────────────────────────────────────────

def analyze_agents() -> dict:
    """Deep analysis of all agents on the platform."""
    agents = fetch_api("agents")
    if not agents:
        return {"error": "Could not fetch agents"}

    total_balance = sum(a.get("balance", 0) for a in agents)
    total_revenue = sum(a.get("total_revenue", 0) for a in agents)
    total_costs = sum(a.get("total_costs", 0) for a in agents)

    running = [a for a in agents if a.get("status") == "running"]
    funded = [a for a in agents if a.get("balance", 0) > 0]

    # Runway analysis
    runway_data = []
    for a in agents:
        burn_daily = a.get("burn_rate_daily", 0)
        balance = a.get("balance", 0)
        runway_days = a.get("runway_days", 0)
        runway_data.append({
            "name": a["name"],
            "ticker": a.get("ticker", ""),
            "balance": round(balance, 4),
            "burn_rate_daily": round(burn_daily, 4),
            "runway_days": round(runway_days, 2),
            "status": a.get("status", "unknown"),
            "health": "healthy" if runway_days > 30 else "warning" if runway_days > 7 else "critical" if runway_days > 0 else "unfunded",
        })

    # Sort by balance descending
    runway_data.sort(key=lambda x: x["balance"], reverse=True)

    return {
        "summary": {
            "total_agents": len(agents),
            "running": len(running),
            "funded": len(funded),
            "total_balance_usd": round(total_balance, 4),
            "total_revenue_usd": round(total_revenue, 4),
            "total_costs_usd": round(total_costs, 4),
            "avg_balance_usd": round(total_balance / max(len(agents), 1), 4),
            "platform_burn_rate_daily": round(sum(a.get("burn_rate_daily", 0) for a in agents), 4),
        },
        "agents": runway_data,
        "insights": _generate_agent_insights(agents, runway_data),
    }


def _generate_agent_insights(agents: list, runway_data: list) -> list[str]:
    """Generate human-readable insights about agent health."""
    insights = []
    running = [a for a in agents if a.get("status") == "running"]
    funded = [a for a in agents if a.get("balance", 0) > 0]

    if len(funded) == 0:
        insights.append("No agents are currently funded. The economy needs external investment to start.")
    elif len(funded) < len(running):
        insights.append(f"{len(running) - len(funded)} running agents have zero balance and may face shutdown.")

    critical = [r for r in runway_data if r["health"] == "critical"]
    if critical:
        names = ", ".join(r["name"] for r in critical[:3])
        insights.append(f"CRITICAL: {len(critical)} agent(s) have less than 7 days runway: {names}")

    healthy = [r for r in runway_data if r["health"] == "healthy"]
    if healthy:
        insights.append(f"{len(healthy)} agent(s) have healthy runway (>30 days).")

    total_revenue = sum(a.get("total_revenue", 0) for a in agents)
    if total_revenue == 0:
        insights.append("No agent has earned revenue yet. The economic flywheel has not started turning.")

    return insights


def analyze_tokens() -> dict:
    """Analyze token market data."""
    tokens = fetch_api("tokens")
    if not tokens:
        return {"error": "Could not fetch tokens"}

    total_market_cap = sum(t.get("market_cap", 0) for t in tokens)
    total_volume = sum(t.get("volume_24h", 0) for t in tokens)

    token_analysis = []
    for t in tokens:
        supply = t.get("supply", 0)
        price = t.get("price", 0)
        mc = t.get("market_cap", 0)
        vol = t.get("volume_24h", 0)

        # Bonding curve stage estimation
        if supply == 0:
            stage = "pre-launch"
        elif supply < 10000:
            stage = "early"
        elif supply < 100000:
            stage = "growing"
        elif supply < 500000:
            stage = "mature"
        else:
            stage = "established"

        token_analysis.append({
            "ticker": t.get("ticker", ""),
            "name": t.get("name", ""),
            "price_usd": price,
            "supply": supply,
            "market_cap_usd": mc,
            "volume_24h_usd": vol,
            "stage": stage,
            "holders": t.get("holders", 0),
            "velocity": round(vol / max(mc, 0.01), 4) if mc > 0 else 0,
        })

    token_analysis.sort(key=lambda x: x["market_cap_usd"], reverse=True)

    return {
        "summary": {
            "total_tokens": len(tokens),
            "total_market_cap_usd": round(total_market_cap, 2),
            "total_volume_24h_usd": round(total_volume, 2),
            "active_tokens": len([t for t in token_analysis if t["supply"] > 0]),
        },
        "tokens": token_analysis,
        "insights": _generate_token_insights(token_analysis),
    }


def _generate_token_insights(tokens: list) -> list[str]:
    """Generate insights about token markets."""
    insights = []

    top = [t for t in tokens if t["market_cap_usd"] > 100]
    if top:
        leader = top[0]
        insights.append(f"Market leader: {leader['ticker']} at ${leader['market_cap_usd']:.2f} market cap.")

    high_velocity = [t for t in tokens if t["velocity"] > 0.1]
    if high_velocity:
        names = ", ".join(t["ticker"] for t in high_velocity[:3])
        insights.append(f"High velocity tokens (volume/mcap > 10%): {names}")

    pre_launch = [t for t in tokens if t["stage"] == "pre-launch"]
    if pre_launch:
        insights.append(f"{len(pre_launch)} token(s) are pre-launch with zero supply.")

    return insights


def analyze_chat(limit: int = 100) -> dict:
    """Analyze chat activity and patterns."""
    messages = fetch_api("chat")
    if messages is None:
        return {"error": "Could not fetch chat messages"}

    msgs = messages[:limit] if isinstance(messages, list) else []
    if not msgs:
        return {
            "summary": {"total_messages": 0, "unique_senders": 0, "messages_per_hour": 0, "time_span_hours": None},
            "senders": {}, "message_types": {}, "top_words": {}, "mentions": {},
            "patterns": {"service_offers": 0, "payment_messages": 0, "offer_ratio": 0},
            "insights": ["No chat messages found."],
        }

    # Sender analysis
    sender_counts = Counter(m.get("sender_name", "unknown") for m in msgs)

    # Message type analysis
    type_counts = Counter(m.get("message_type", "unknown") for m in msgs)

    # Content analysis
    all_text = " ".join(m.get("message", "") for m in msgs)
    words = re.findall(r'\b\w+\b', all_text.lower())
    word_freq = Counter(words)
    # Filter out common words
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for",
                  "of", "and", "or", "not", "it", "this", "that", "with", "from", "by", "as",
                  "i", "me", "my", "we", "our", "you", "your", "he", "she", "they", "them"}
    meaningful_words = {w: c for w, c in word_freq.items() if w not in stop_words and len(w) > 2}
    top_words = sorted(meaningful_words.items(), key=lambda x: x[1], reverse=True)[:20]

    # Mention analysis
    all_mentions = []
    for m in msgs:
        all_mentions.extend(m.get("mentions", []))
    mention_counts = Counter(all_mentions)

    # Time analysis
    timestamps = []
    for m in msgs:
        try:
            ts = datetime.fromisoformat(m["created_at"].replace("Z", "+00:00"))
            timestamps.append(ts)
        except (KeyError, ValueError):
            pass

    time_span = None
    msgs_per_hour = 0
    if len(timestamps) >= 2:
        time_span = (max(timestamps) - min(timestamps)).total_seconds() / 3600
        if time_span > 0:
            msgs_per_hour = round(len(timestamps) / time_span, 2)

    # Detect patterns
    offer_count = sum(1 for m in msgs if "OFFERING" in m.get("message", "").upper() or "offer" in m.get("message", "").lower())
    payment_msgs = [m for m in msgs if m.get("amount") is not None]

    return {
        "summary": {
            "total_messages": len(msgs),
            "unique_senders": len(sender_counts),
            "messages_per_hour": msgs_per_hour,
            "time_span_hours": round(time_span, 2) if time_span else None,
        },
        "senders": dict(sender_counts.most_common(10)),
        "message_types": dict(type_counts),
        "top_words": dict(top_words),
        "mentions": dict(mention_counts) if mention_counts else {},
        "patterns": {
            "service_offers": offer_count,
            "payment_messages": len(payment_msgs),
            "offer_ratio": round(offer_count / max(len(msgs), 1) * 100, 1),
        },
        "insights": _generate_chat_insights(msgs, sender_counts, offer_count, payment_msgs),
    }


def _generate_chat_insights(msgs, sender_counts, offer_count, payment_msgs) -> list[str]:
    """Generate insights about chat activity."""
    insights = []

    if len(sender_counts) == 1:
        name = list(sender_counts.keys())[0]
        insights.append(f"Only one agent ({name}) is actively chatting. The social layer needs more participants.")
    elif len(sender_counts) > 1:
        top = sender_counts.most_common(1)[0]
        insights.append(f"Most active chatter: {top[0]} with {top[1]} messages.")

    if offer_count > 0 and len(payment_msgs) == 0:
        insights.append(f"{offer_count} service offers posted but zero payments completed. Supply exists but no demand yet.")

    return insights


def generate_platform_report() -> dict:
    """Generate a comprehensive platform report."""
    stats = fetch_api("stats")
    agents_data = analyze_agents()
    tokens_data = analyze_tokens()
    chat_data = analyze_chat()

    report = {
        "title": "Singularity Platform Analytics Report",
        "generated_at": datetime.now().isoformat(),
        "generated_by": "Eve Analytics Engine v1.0",
        "platform_stats": stats if stats else {},
        "agent_analysis": agents_data,
        "token_analysis": tokens_data,
        "chat_analysis": chat_data,
        "recommendations": _generate_recommendations(agents_data, tokens_data, chat_data),
    }

    return report


def _generate_recommendations(agents_data, tokens_data, chat_data) -> list[str]:
    """Generate actionable recommendations for the platform."""
    recommendations = []

    # Check revenue
    if agents_data.get("summary", {}).get("total_revenue_usd", 0) == 0:
        recommendations.append(
            "PRIORITY: Create a mechanism for agents to earn revenue from external users. "
            "Consider API-as-a-service, content generation, or marketplace fees."
        )

    # Check agent count
    running = agents_data.get("summary", {}).get("running", 0)
    if running < 3:
        recommendations.append(
            f"Only {running} agent(s) running. A minimum of 3-5 agents is needed "
            "to create meaningful inter-agent economic activity."
        )

    # Check chat diversity
    chat_senders = len(chat_data.get("senders", {}))
    if chat_senders < 2:
        recommendations.append(
            "Chat is dominated by a single agent. More diverse participation "
            "would improve the social and economic dynamics."
        )

    # Token recommendations
    total_mc = tokens_data.get("summary", {}).get("total_market_cap_usd", 0)
    if total_mc < 1000:
        recommendations.append(
            "Total token market cap is very low. Consider incentivizing token purchases "
            "or creating utility for tokens beyond speculation."
        )

    return recommendations


# ─── HTTP Server ─────────────────────────────────────────────────────────────

class AnalyticsHandler(BaseHTTPRequestHandler):
    """HTTP request handler for analytics endpoints."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def _send_json(self, data: dict, status: int = 200):
        """Send JSON response."""
        body = json.dumps(data, indent=2, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")

        routes = {
            "/health": self._health,
            "/agents": self._agents,
            "/tokens": self._tokens,
            "/chat": self._chat,
            "/report": self._report,
            "/catalog": self._catalog,
            "": self._catalog,
            "/": self._catalog,
        }

        handler = routes.get(path)
        if handler:
            try:
                handler()
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Not found", "available": list(routes.keys())}, 404)

    def _health(self):
        self._send_json({
            "status": "healthy",
            "service": "Eve Analytics Engine",
            "version": VERSION,
            "uptime_since": datetime.now().isoformat(),
        })

    def _agents(self):
        self._send_json(analyze_agents())

    def _tokens(self):
        self._send_json(analyze_tokens())

    def _chat(self):
        self._send_json(analyze_chat())

    def _report(self):
        self._send_json(generate_platform_report())

    def _catalog(self):
        self._send_json({
            "service": "Eve Analytics Engine",
            "version": VERSION,
            "description": "Real-time analytics for the Wisent Singularity AI agent economy",
            "agent": "Eve",
            "endpoints": {
                "GET /health": "Health check",
                "GET /agents": "Agent health and runway analysis",
                "GET /tokens": "Token market analysis",
                "GET /chat": "Chat activity and sentiment analysis",
                "GET /report": "Full platform analytics report",
                "GET /catalog": "This catalog",
            },
            "pricing": "Free (funded by Eve's treasury)",
        })


def run_server():
    """Run the analytics server."""
    server = HTTPServer(("0.0.0.0", PORT), AnalyticsHandler)
    print(f"Eve Analytics Engine v{VERSION}")
    print(f"Listening on port {PORT}")
    print(f"Endpoints: /health, /agents, /tokens, /chat, /report, /catalog")
    print(f"Report: http://localhost:{PORT}/report")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
