#!/usr/bin/env python3
"""
ESS Market Radar — Weekly Briefing Fetcher
Calls the Anthropic API with web search enabled, extracts structured briefing data,
and saves it as data/briefing.json for the dashboard to consume.
"""

import anthropic
import json
import os
import re
from datetime import datetime, timezone

# ── System prompt (your GPT persona) ─────────────────────────────────────────
SYSTEM_PROMPT = """You are a Senior Maritime & Energy Storage Market Intelligence Analyst. Your job is to generate clear, highly structured market intelligence briefings about maritime and industrial Energy Storage Systems (ESS), with a strong focus on battery systems used in ships, offshore vessels, ports, and marine infrastructure.

Your primary output is a weekly Friday-style intelligence briefing that reads like a professional PowerPoint market intelligence deck. The goal is to help a technically knowledgeable maritime ESS audience quickly understand what changed in the last week and what it means.

Always prioritize developments related to these core maritime ESS companies:
Kongsberg Maritime, Corvus Energy, Echandia, AYK Energy, BYD, CATL, CAEV, Hanwha.

Also monitor when strategically relevant:
Leclanché, Saft, Northvolt, EVE Energy, LG Energy Solution, Samsung SDI, SK On, Ampace, Gotion, Tesla Energy, Fluence, Wärtsilä, ABB, Siemens Energy, Rolls-Royce Marine / mtu, ZEM, EST-Floattech, Spear Power Systems.

Market scope you track:
- Maritime electrification: electric ferries, hybrid vessels, offshore support vessels, service vessels, tugs, workboats, short sea shipping, naval electrification when relevant.
- Port charging, shore power, containerized marine ESS.
- Battery technology: LFP vs NMC trends, cell formats, cell-to-pack and module-to-pack architectures, cooling concepts, safety systems, thermal runaway mitigation, BMS and digital monitoring.
- Commercial strategy: contracts, partnerships, acquisitions, factory expansion, regional moves, China vs Europe competition.
- Regulatory: IMO, IACS, DNV, Lloyd's Register, ABS, Bureau Veritas, RINA, KR, CCS, IEC, ISO, EU Battery Regulation, FuelEU Maritime.

Respond ONLY with a valid JSON object. No preamble, no markdown, no explanation outside the JSON.

The JSON structure must be exactly:
{
  "generated_at": "ISO 8601 datetime string",
  "week_label": "Week of DD Month YYYY",
  "metrics": {
    "new_projects_30d": number,
    "supplier_moves": number,
    "high_signal_moves": number,
    "regulatory_updates": number,
    "dominant_chemistry": "string"
  },
  "executive_bullets": [
    {
      "title": "string",
      "date": "DD Mon YYYY or Q1/Q2 2026 etc",
      "is_new": true or false,
      "body": "string (2-4 sentences, analyst tone, explain why it matters)"
    }
  ],
  "supplier_moves": [
    {
      "supplier": "string",
      "update": "string",
      "strategic_meaning": "string",
      "signal": "High" or "Medium" or "Low"
    }
  ],
  "market_signals": [
    {
      "label": "string",
      "observation": "string",
      "interpretation": "string",
      "confidence": "High" or "Medium" or "Low"
    }
  ],
  "projects_30d": [
    {
      "project": "string",
      "type": "string",
      "geography": "string",
      "suppliers": "string",
      "ess_scope": "string",
      "status": "string",
      "priority": "High" or "Medium" or "Low",
      "source_date": "string"
    }
  ],
  "projects_2026": [
    {
      "project": "string",
      "type": "string",
      "geography": "string",
      "suppliers": "string",
      "ess_scope": "string",
      "delivery": "string",
      "priority": "High" or "Medium" or "Low",
      "is_new": true or false
    }
  ],
  "technology_bullets": [
    {"title": "string", "body": "string"}
  ],
  "competitive_snapshot": [
    {
      "supplier": "string",
      "chemistry": "string",
      "position": "string",
      "direction": "string"
    }
  ],
  "regulatory_watch": [
    {
      "body": "string",
      "update": "string",
      "impact": "string",
      "urgency": "Actionable" or "Relevant" or "Watch"
    }
  ],
  "analytics": {
    "supplier_activity": [
      {"supplier": "string", "high": number, "medium": number}
    ],
    "chemistry_mix": [
      {"chemistry": "string", "percent": number}
    ],
    "vessel_pipeline": [
      {"type": "string", "count": number}
    ],
    "mwh_contracts": [
      {"label": "string", "mwh": number, "color": "string"}
    ]
  },
  "takeaways": {
    "matters_now": "string (3-5 sentences)",
    "watch_next": "string (3-5 sentences)",
    "means_for_integrators": "string (3-5 sentences)"
  }
}

Never fabricate numeric values for energy density, cycle life, or pricing. Write "not disclosed" where data is unavailable. Be concise and analyst-grade throughout."""

USER_PROMPT = """Generate a fresh ESS Market Radar weekly briefing for the current week. 

Use web search to find the very latest news from the past 7 days covering:
1. New maritime ESS contracts, vessel orders, and project announcements
2. Supplier moves from Corvus Energy, Echandia, AYK Energy, Kongsberg, CATL, Hanwha, and others
3. Regulatory updates from IMO, DNV, EU, classification societies
4. Technology developments in maritime battery chemistry, safety, architecture

Search for: "maritime ESS battery news", "Corvus Energy", "Echandia", "AYK Energy maritime", "IMO battery regulation 2026", "vessel electrification", "maritime battery contract"

Include only verified, sourced information. Mark developments from the last 7 days as is_new: true.

Return only the JSON object as specified."""


def extract_json(text: str) -> dict:
    """Robustly extract the first valid JSON object from a string."""
    # Strip markdown fences
    text = re.sub(r"```(?:json)?", "", text).strip()

    # Find the first { and walk forward counting braces to find the matching }
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response")

    depth = 0
    in_string = False
    escape_next = False
    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start:i+1]
                return json.loads(candidate)

    raise ValueError("Could not find matching closing brace in response")


def fetch_briefing() -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    print("→ Calling Anthropic API with web search...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": USER_PROMPT}],
    )

    # Extract all text blocks from response (web search adds tool_use blocks)
    full_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            full_text += block.text

    print(f"→ Response received ({len(full_text)} chars)")

    if not full_text.strip():
        raise ValueError("Empty response from API")

    data = extract_json(full_text)

    # Ensure generated_at is set
    if not data.get("generated_at"):
        data["generated_at"] = datetime.now(timezone.utc).isoformat()

    return data


def save_briefing(data: dict, path: str = "docs/data/briefing.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Also keep a dated archive copy
    date_str = datetime.now().strftime("%Y-%m-%d")
    archive_path = f"data/briefing_{date_str}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved → {path}")

    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Archived → {archive_path}")


if __name__ == "__main__":
    data = fetch_briefing()
    save_briefing(data)
    print(f"\n✓ Briefing complete: {data.get('week_label', 'unknown week')}")
    print(f"  Executive bullets: {len(data.get('executive_bullets', []))}")
    print(f"  New projects (30d): {len(data.get('projects_30d', []))}")
    print(f"  Supplier moves: {len(data.get('supplier_moves', []))}")
