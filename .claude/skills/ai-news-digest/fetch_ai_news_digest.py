#!/usr/bin/env python3
"""
AI News Digest - Fetch latest AI news via Perplexity and deliver via Slack.

Follows directive: directives/ai_news_digest.md

Usage:
    python3 execution/fetch_ai_news_digest.py
    python3 execution/fetch_ai_news_digest.py --topic "AI agents"
    python3 execution/fetch_ai_news_digest.py --count 10
    python3 execution/fetch_ai_news_digest.py --topic "LLMs" --count 5 --no-slack
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()


def call_perplexity(query: str, api_key: str) -> str:
    """Call Perplexity API with a research query."""
    url = "https://api.perplexity.ai/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "user",
                "content": query,
            }
        ],
        "temperature": 0.2,
        "max_tokens": 3000,
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        print(f"Perplexity API error: {response.status_code}")
        print(f"   Response: {response.text}")
        return ""

    result = response.json()
    return result["choices"][0]["message"]["content"]


def fetch_ai_news(topic: str, count: int, api_key: str) -> str:
    """Fetch latest AI news articles from Perplexity."""
    today = datetime.now().strftime("%B %d, %Y")

    query = f"""Find the {count} most important and recent news articles about {topic} from today or this week (today is {today}).

For each article, provide EXACTLY this format:

ARTICLE 1:
Title: [exact headline]
Source: [publication name]
URL: [full URL to the article]
Summary: [one-sentence summary of the key finding or announcement]

ARTICLE 2:
Title: ...
(continue for all {count} articles)

Requirements:
- Only include real, verifiable articles from the past 7 days
- Prioritize major announcements, product launches, research breakthroughs, and industry moves
- Include the actual URL to each article
- Each summary should be exactly one sentence"""

    print(f"Querying Perplexity for {count} latest articles on '{topic}'...")
    return call_perplexity(query, api_key)


def parse_articles(raw_text: str, count: int) -> list:
    """Parse raw Perplexity response into structured article dicts."""
    articles = []
    current = {}

    for line in raw_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.lower().startswith("title:"):
            if current.get("title"):
                articles.append(current)
                current = {}
            current["title"] = line.split(":", 1)[1].strip()
        elif line.lower().startswith("source:"):
            current["source"] = line.split(":", 1)[1].strip()
        elif line.lower().startswith("url:"):
            current["url"] = line.split(":", 1)[-1].strip()
            # Handle "URL: https://..." where split on : breaks the URL
            if not current["url"].startswith("http"):
                # Reconstruct URL from the original line
                url_start = line.find("http")
                if url_start != -1:
                    current["url"] = line[url_start:].strip()
        elif line.lower().startswith("summary:"):
            current["summary"] = line.split(":", 1)[1].strip()

    # Don't forget the last article
    if current.get("title"):
        articles.append(current)

    # Validate each article has required fields
    validated = []
    for article in articles[:count]:
        if article.get("title") and article.get("summary"):
            validated.append({
                "title": article.get("title", "Untitled"),
                "source": article.get("source", "Unknown"),
                "url": article.get("url", ""),
                "summary": article.get("summary", ""),
            })

    return validated


def save_digest_locally(articles: list, topic: str) -> str:
    """Save digest as Markdown to .tmp/ai_news_digest/."""
    output_dir = Path(__file__).parent.parent / ".tmp" / "ai_news_digest"
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"digest_{date_str}.md"
    filepath = output_dir / filename

    lines = [
        f"# AI News Digest - {topic.title()}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}",
        f"**Topic:** {topic}",
        f"**Articles:** {len(articles)}",
        "",
        "---",
        "",
    ]

    for i, article in enumerate(articles, 1):
        url_text = f"[Read Article]({article['url']})" if article["url"] else "No URL available"
        lines.extend([
            f"## {i}. {article['title']}",
            f"**Source:** {article['source']} | {url_text}",
            "",
            f"{article['summary']}",
            "",
            "---",
            "",
        ])

    filepath.write_text("\n".join(lines))
    print(f"Digest saved to: {filepath}")
    return str(filepath)


def send_to_slack(articles: list, topic: str) -> dict:
    """Send formatted digest to Slack via webhook."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if not webhook_url:
        print("SLACK_WEBHOOK_URL not configured - skipping Slack delivery")
        return {"sent": False, "reason": "No webhook URL"}

    # Build Slack Block Kit message
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"AI News Digest: {topic.title()}"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"{len(articles)} articles | {datetime.now().strftime('%B %d, %Y')}"
                }
            ]
        },
        {"type": "divider"},
    ]

    for i, article in enumerate(articles, 1):
        # Article title with link
        if article["url"]:
            title_text = f"*{i}. <{article['url']}|{article['title']}>*"
        else:
            title_text = f"*{i}. {article['title']}*"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{title_text}\n_{article['source']}_\n{article['summary']}"
            }
        })

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Generated by AIAA Agentic OS | {datetime.now().strftime('%H:%M:%S')}"
            }
        ]
    })

    message = {
        "text": f"AI News Digest: {topic.title()} - {len(articles)} articles",
        "blocks": blocks,
    }

    try:
        response = requests.post(webhook_url, json=message)

        if response.status_code == 200:
            print("Slack notification sent successfully")
            return {
                "sent": True,
                "status_code": response.status_code,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            print(f"Slack error: {response.status_code} - {response.text}")
            return {
                "sent": False,
                "status_code": response.status_code,
                "error": response.text,
            }

    except Exception as e:
        print(f"Slack delivery failed: {e}")
        return {"sent": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Fetch latest AI news and deliver via Slack")
    parser.add_argument("--topic", default="artificial intelligence", help="News topic to search (default: artificial intelligence)")
    parser.add_argument("--count", type=int, default=5, help="Number of articles to find (default: 5)")
    parser.add_argument("--no-slack", action="store_true", help="Skip Slack delivery")
    args = parser.parse_args()

    # --- Prerequisite check ---
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        print("Error: PERPLEXITY_API_KEY not set in environment")
        sys.exit(1)

    print(f"=== AI News Digest ===")
    print(f"Topic: {args.topic}")
    print(f"Count: {args.count}")
    print(f"Slack: {'disabled' if args.no_slack else 'enabled'}")
    print()

    # --- Step 1: Fetch news from Perplexity ---
    raw_response = fetch_ai_news(args.topic, args.count, api_key)
    if not raw_response:
        print("Error: No response from Perplexity API")
        sys.exit(1)

    # --- Step 2: Parse articles ---
    articles = parse_articles(raw_response, args.count)
    if not articles:
        print("Error: Could not parse any articles from response")
        print(f"Raw response:\n{raw_response}")
        sys.exit(1)

    print(f"Found {len(articles)} articles")
    if len(articles) < args.count:
        print(f"Warning: Requested {args.count} but only found {len(articles)}")
    print()

    # --- Step 3: Display articles ---
    for i, article in enumerate(articles, 1):
        print(f"{i}. {article['title']}")
        print(f"   Source: {article['source']}")
        print(f"   URL: {article['url']}")
        print(f"   Summary: {article['summary']}")
        print()

    # --- Step 4: Save locally ---
    filepath = save_digest_locally(articles, args.topic)

    # --- Step 5: Send to Slack ---
    if not args.no_slack:
        slack_result = send_to_slack(articles, args.topic)
        if not slack_result.get("sent"):
            print(f"Warning: Slack delivery failed - {slack_result.get('reason', slack_result.get('error', 'unknown'))}")
    else:
        print("Slack delivery skipped (--no-slack flag)")

    print()
    print(f"=== Done ===")
    print(f"Digest saved to: {filepath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
