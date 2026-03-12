#!/usr/bin/env python3
"""
Tool: News Relevance Scorer
Purpose: Score news items for YouTube channel relevance using LLM-as-Judge

Uses OpenAI GPT-4o (or Claude) to evaluate news items against channel context
and content pillars. Returns relevance score, tier, reasoning, and suggested angles.

API: OpenAI (gpt-4o) or Anthropic (claude-3-5-sonnet)
Env Vars: OPENAI_API_KEY or ANTHROPIC_API_KEY

Usage:
    python tools/news_monitor/score_relevance.py --title "Title" --source hackernews --url "https://..."
    python tools/news_monitor/score_relevance.py --items-file items.json
    python tools/news_monitor/score_relevance.py --items-file items.json --model claude

Dependencies:
    - openai or anthropic
    - requests (for Helicone proxy)

Output:
    JSON with scored items
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Resolve plugin root
PLUGIN_ROOT = os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    str(Path(__file__).resolve().parent.parent.parent)
)
SKILL_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = Path(PLUGIN_ROOT).parent  # project root (parent of plugin)
PROMPT_PATH = SKILL_DIR / "references" / "score_relevance.md"

# Load .env from project root
try:
    from dotenv import load_dotenv
    load_dotenv(WORKSPACE_ROOT / ".env")
except ImportError:
    pass

# Model configs
MODELS = {
    "gpt4": {
        "provider": "openai",
        "model": "gpt-4o",
        "env_key": "OPENAI_API_KEY"
    },
    "gpt4-mini": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY"
    },
    "claude": {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "env_key": "ANTHROPIC_API_KEY"
    },
    "haiku": {
        "provider": "anthropic",
        "model": "claude-haiku-4-5-20251001",
        "env_key": "ANTHROPIC_API_KEY"
    }
}


def load_business_profile() -> str:
    """Load business profile for DRIFT test scoring.

    Returns the full file content, or a fallback string if the profile
    is missing or still a placeholder.
    """
    profile_path = WORKSPACE_ROOT / "context" / "my-business.md"

    if not profile_path.exists():
        return "Business profile not configured — skip DRIFT assessment, set all drift fields to null."

    content = profile_path.read_text()

    # Check if it's still the placeholder
    if "placeholder" in content.lower() or "business-setup wizard" in content.lower():
        return "Business profile not configured — skip DRIFT assessment, set all drift fields to null."

    return content


def load_prompt_template(include_drift: bool = True) -> str:
    """Load the scoring prompt template, optionally with DRIFT test section.

    Args:
        include_drift: If True, inject the business profile into the DRIFT section.
                      If False, strip the DRIFT section entirely.
    """
    if PROMPT_PATH.exists():
        template = PROMPT_PATH.read_text()
    else:
        # Fallback inline prompt if file doesn't exist
        template = """Score this AI news item for relevance to a YouTube channel about AI for business operations.

Target: Mid-market operations leaders (COO, VP Ops)
Focus: AI workflow automation, agents, Claude, MCP, n8n

Score 8-10 (high): Breaking tools, viral techniques, contrarian takes, enterprise ROI
Score 5-7 (medium): General LLM updates, productivity tools
Score 2-4 (low): Academic papers, infrastructure news
Score 1 (noise): Consumer AI, art, funding news

Viral boost (+1-2): Simple beats complex, "just use X" format, named techniques

Title: {title}
Source: {source}
URL: {url}
Summary: {summary}

Respond with JSON only:
{{"relevance_score": <1-10>, "relevance_tier": "<high|medium|low|noise>", "relevance_reasoning": "<why>", "content_angle": "<video idea or null>", "topics_matched": [], "viral_indicators": []}}"""
        return template

    if include_drift:
        # Inject business profile into the DRIFT section
        business_profile = load_business_profile()
        template = template.replace("{business_profile}", business_profile)
    else:
        # Strip the DRIFT section from the prompt and response format
        drift_marker = "## BUSINESS IMPACT ASSESSMENT (DRIFT Test)"
        if drift_marker in template:
            template = template[:template.index(drift_marker)]
            # Re-append a minimal response format without drift fields
            template += """## NEWS ITEM TO SCORE

Title: {title}
Source: {source}
URL: {url}
Summary: {summary}
Author: {author}

## RESPONSE FORMAT

Respond with valid JSON only:
```json
{{
  "relevance_score": <number>,
  "relevance_tier": "<high|medium|low|noise>",
  "relevance_reasoning": "<string>",
  "content_angle": "<string or null>",
  "topics_matched": ["<topic1>", "<topic2>"],
  "viral_indicators": ["<indicator1>"]
}}
```"""

    return template


def score_with_openai(
    prompt: str,
    model: str,
    api_key: str,
    temperature: float = 0.1
) -> dict:
    """Score using OpenAI API."""
    try:
        import openai
    except ImportError:
        return {"success": False, "error": "Missing dependency: openai. Run: pip install openai"}

    # Check for Helicone proxy
    helicone_key = os.getenv("HELICONE_API_KEY")
    if helicone_key:
        base_url = "https://oai.helicone.ai/v1"
        default_headers = {"Helicone-Auth": f"Bearer {helicone_key}"}
        client = openai.OpenAI(api_key=api_key, base_url=base_url, default_headers=default_headers)
    else:
        client = openai.OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a news relevance scorer. Respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=500,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        return {"success": True, "result": json.loads(content)}

    except Exception as e:
        return {"success": False, "error": str(e)}


def score_with_anthropic(
    prompt: str,
    model: str,
    api_key: str,
    temperature: float = 0.1
) -> dict:
    """Score using Anthropic API."""
    try:
        import anthropic
    except ImportError:
        return {"success": False, "error": "Missing dependency: anthropic. Run: pip install anthropic"}

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=500,
            temperature=temperature,
            messages=[
                {"role": "user", "content": prompt + "\n\nRespond with valid JSON only, no markdown."}
            ]
        )

        content = response.content[0].text
        # Clean potential markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        return {"success": True, "result": json.loads(content.strip())}

    except Exception as e:
        return {"success": False, "error": str(e)}


def score_item(
    title: str,
    source: str,
    url: str = None,
    summary: str = None,
    author: str = None,
    model_name: str = "gpt4-mini",
    prompt_template: str = None,
    include_drift: bool = True
) -> dict:
    """
    Score a single news item for relevance.

    Args:
        title: Item title
        source: Source name (hackernews, github, etc.)
        url: Item URL
        summary: Brief description
        author: Author name
        model_name: Model to use (gpt4, gpt4-mini, claude)
        prompt_template: Custom prompt template

    Returns:
        dict with scoring results
    """
    model_config = MODELS.get(model_name, MODELS["gpt4-mini"])
    api_key = os.getenv(model_config["env_key"])

    if not api_key:
        return {
            "success": False,
            "error": f"{model_config['env_key']} environment variable not set"
        }

    # Load prompt template
    if not prompt_template:
        prompt_template = load_prompt_template(include_drift=include_drift)

    # Build prompt
    prompt = prompt_template.format(
        title=title,
        source=source,
        url=url or "N/A",
        summary=summary or "No summary available",
        author=author or "Unknown"
    )

    # Score based on provider
    if model_config["provider"] == "openai":
        result = score_with_openai(prompt, model_config["model"], api_key)
    else:
        result = score_with_anthropic(prompt, model_config["model"], api_key)

    if not result.get("success"):
        return result

    # Add metadata
    scoring = result["result"]
    scoring["model_used"] = model_config["model"]

    # Determine tier from score if not provided
    if "relevance_tier" not in scoring and "relevance_score" in scoring:
        score = scoring["relevance_score"]
        if score >= 8:
            scoring["relevance_tier"] = "high"
        elif score >= 5:
            scoring["relevance_tier"] = "medium"
        elif score >= 2:
            scoring["relevance_tier"] = "low"
        else:
            scoring["relevance_tier"] = "noise"

    return {
        "success": True,
        "item": {
            "title": title,
            "source": source,
            "url": url
        },
        "scoring": scoring
    }


def score_items_batch(
    items: list,
    model_name: str = "gpt4-mini",
    min_score_to_keep: int = 2,
    include_drift: bool = True
) -> dict:
    """
    Score multiple items.

    Args:
        items: List of item dicts with title, source, url, summary
        model_name: Model to use
        min_score_to_keep: Minimum score to include in results
        include_drift: Include DRIFT business impact scoring

    Returns:
        dict with scored items
    """
    prompt_template = load_prompt_template(include_drift=include_drift)

    scored = []
    errors = []

    for i, item in enumerate(items):
        print(f"Scoring {i+1}/{len(items)}: {item.get('title', 'Unknown')[:50]}...", file=sys.stderr)

        result = score_item(
            title=item.get("title", ""),
            source=item.get("source", "unknown"),
            url=item.get("url"),
            summary=item.get("summary"),
            author=item.get("author"),
            model_name=model_name,
            prompt_template=prompt_template
        )

        if result.get("success"):
            scoring = result["scoring"]
            if scoring.get("relevance_score", 0) >= min_score_to_keep:
                scored.append({
                    **item,
                    **scoring
                })
        else:
            errors.append({
                "item": item.get("title"),
                "error": result.get("error")
            })

    # Sort by score
    scored.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    # Group by tier
    high = [i for i in scored if i.get("relevance_tier") == "high"]
    medium = [i for i in scored if i.get("relevance_tier") == "medium"]
    low = [i for i in scored if i.get("relevance_tier") == "low"]

    return {
        "success": True,
        "total_scored": len(items),
        "total_kept": len(scored),
        "high_priority": len(high),
        "medium_priority": len(medium),
        "low_priority": len(low),
        "errors": len(errors),
        "scored_items": scored,
        "error_items": errors if errors else None,
        "model_used": model_name
    }


def main():
    parser = argparse.ArgumentParser(
        description="Score news items for YouTube channel relevance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Score a single item
  python score_relevance.py --title "Claude 4 Released" --source hackernews --url "https://..."

  # Score from JSON file
  python score_relevance.py --items-file scraped_items.json

  # Use Claude instead of GPT
  python score_relevance.py --items-file items.json --model claude

  # Only keep high-scoring items
  python score_relevance.py --items-file items.json --min-score 5
        """
    )

    parser.add_argument("--title", help="Item title (for single item)")
    parser.add_argument("--source", help="Source name (for single item)")
    parser.add_argument("--url", help="Item URL (for single item)")
    parser.add_argument("--summary", help="Item summary (for single item)")
    parser.add_argument("--author", help="Item author (for single item)")
    parser.add_argument("--items-file", "-f", help="JSON file with items to score")
    parser.add_argument("--model", "-m", choices=["gpt4", "gpt4-mini", "claude", "haiku"],
                       default="haiku", help="Model to use (default: haiku)")
    parser.add_argument("--min-score", type=int, default=2,
                       help="Minimum score to keep (default: 2)")
    parser.add_argument("--no-drift", action="store_true",
                       help="Skip DRIFT business impact scoring (community relevance only)")
    parser.add_argument("--output", "-o", help="Save output to file")

    args = parser.parse_args()

    include_drift = not args.no_drift

    # Single item mode
    if args.title:
        if not args.source:
            print(json.dumps({"success": False, "error": "--source required with --title"}))
            sys.exit(1)

        result = score_item(
            title=args.title,
            source=args.source,
            url=args.url,
            summary=args.summary,
            author=args.author,
            model_name=args.model,
            include_drift=include_drift
        )

    # Batch mode from file
    elif args.items_file:
        with open(args.items_file) as f:
            data = json.load(f)

        # Handle both direct list and {"items": [...]} format
        items = data if isinstance(data, list) else data.get("items", [])

        if not items:
            print(json.dumps({"success": False, "error": "No items found in file"}))
            sys.exit(1)

        result = score_items_batch(
            items=items,
            model_name=args.model,
            min_score_to_keep=args.min_score,
            include_drift=include_drift
        )

    # Stdin
    elif not sys.stdin.isatty():
        data = json.load(sys.stdin)
        items = data if isinstance(data, list) else data.get("items", [])

        result = score_items_batch(
            items=items,
            model_name=args.model,
            min_score_to_keep=args.min_score,
            include_drift=include_drift
        )

    else:
        parser.print_help()
        sys.exit(1)

    # Output
    output = json.dumps(result, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Saved to {args.output}", file=sys.stderr)

    print(output)

    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
