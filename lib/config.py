"""
Configuration loader for content-os plugin.

Reads structured config from .claude/content-os.local.md (YAML frontmatter)
and .env file for API keys. Provides a clean get() API for all plugin components.

Usage:
    from lib.config import get_config, get_key

    config = get_config()
    gemini_key = get_key("gemini")
    links = config.get("social_links", {})
"""

import os
import re
from pathlib import Path


def _find_project_root() -> Path:
    """Walk up from CWD to find the project root (has .claude/ dir)."""
    cwd = Path.cwd()
    for p in [cwd] + list(cwd.parents):
        if (p / ".claude").is_dir():
            return p
    return cwd


def _load_env(env_path: Path) -> dict[str, str]:
    """Load .env file into a dict (does NOT overwrite os.environ)."""
    env_vars = {}
    if not env_path.exists():
        return env_vars
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            env_vars[key] = value
            os.environ.setdefault(key, value)
    return env_vars


def _parse_yaml_frontmatter(text: str) -> dict:
    """Parse YAML frontmatter from markdown file.

    Simple parser that handles the subset we need: scalars, lists, nested dicts.
    No external YAML dependency required.
    """
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    yaml_text = match.group(1)
    result = {}
    current_dict = result
    dict_stack = []
    current_key = None
    indent_stack = [0]

    for line in yaml_text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Calculate indent level
        indent = len(line) - len(line.lstrip())

        # Pop back if we've dedented
        while indent_stack and indent <= indent_stack[-1] and len(dict_stack) > 0:
            indent_stack.pop()
            current_dict = dict_stack.pop() if dict_stack else result

        # List item
        if stripped.startswith("- "):
            value = stripped[2:].strip().strip('"').strip("'")
            if current_key and current_key in current_dict:
                if isinstance(current_dict[current_key], list):
                    current_dict[current_key].append(value)
            continue

        # Key: value pair
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if not value:
                # Could be a dict or list — check next line
                current_dict[key] = {}
                dict_stack.append(current_dict)
                current_dict = current_dict[key]
                current_key = key
                indent_stack.append(indent)
            else:
                current_dict[key] = value
                current_key = key

    # Post-process: convert empty dicts that should be lists
    _fix_empty_containers(result)
    return result


def _fix_empty_containers(d: dict):
    """Convert empty dicts to empty lists where appropriate."""
    for k, v in d.items():
        if isinstance(v, dict):
            if not v:
                # Leave empty dicts as-is
                pass
            else:
                _fix_empty_containers(v)


# ---------------------------------------------------------------------------
# Singleton config cache
# ---------------------------------------------------------------------------

_config: dict | None = None
_env_vars: dict[str, str] = {}


def get_config(force_reload: bool = False) -> dict:
    """Load and return the full plugin config.

    Reads from:
    1. .claude/content-os.local.md (YAML frontmatter) — structured config
    2. .env — API keys and secrets

    Returns a merged dict.
    """
    global _config, _env_vars

    if _config is not None and not force_reload:
        return _config

    root = _find_project_root()

    # Load .env
    _env_vars = _load_env(root / ".env")

    # Load local config
    config_path = root / ".claude" / "content-os.local.md"
    if config_path.exists():
        _config = _parse_yaml_frontmatter(config_path.read_text())
    else:
        _config = {}

    return _config


def get_key(key_name: str) -> str | None:
    """Get an API key by name.

    Checks (in order):
    1. os.environ (already loaded from .env)
    2. config api_keys section
    3. Common environment variable name mappings

    Key name mappings:
        gemini     → GEMINI_API_KEY, GOOGLE_API_KEY
        openai     → OPENAI_API_KEY
        notion     → NOTION_TOKEN, NOTION_API_KEY
        supabase   → SUPABASE_DB_URL
        youtube    → YOUTUBE_DATA_API_KEY
        slack      → SLACK_BOT_TOKEN
        perplexity → PERPLEXITY_API_KEY
    """
    config = get_config()

    # Check config api_keys section first
    api_keys = config.get("api_keys", {})
    if isinstance(api_keys, dict) and api_keys.get(key_name):
        return api_keys[key_name]

    # Environment variable mappings
    env_mappings = {
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "openai": ["OPENAI_API_KEY"],
        "notion": ["NOTION_TOKEN", "NOTION_API_KEY", "NOTION_INTEGRATION_TOKEN"],
        "supabase": ["SUPABASE_DB_URL"],
        "youtube": ["YOUTUBE_DATA_API_KEY"],
        "slack": ["SLACK_BOT_TOKEN"],
        "perplexity": ["PERPLEXITY_API_KEY"],
        "helicone": ["HELICONE_API_KEY"],
    }

    for env_var in env_mappings.get(key_name, [key_name.upper()]):
        val = os.environ.get(env_var)
        if val:
            return val

    return None


def get_social_links() -> dict[str, str]:
    """Get social links from config."""
    config = get_config()
    return config.get("social_links", {})


def get_hashtags() -> str:
    """Get base hashtags string."""
    config = get_config()
    return config.get("hashtags", "#AI #AIAutomation")


def get_about_text() -> str:
    """Get the about/bio text for descriptions and footers."""
    config = get_config()
    return config.get("about_text", "[Set your about text in .claude/content-os.local.md]")


def get_db_backend() -> str:
    """Get database backend: 'sqlite' or 'supabase'."""
    config = get_config()
    db_config = config.get("database", {})
    if isinstance(db_config, dict):
        return db_config.get("backend", "sqlite")
    return "sqlite"


def get_output_destination() -> str:
    """Get output destination: 'local' or 'notion'."""
    config = get_config()
    output = config.get("output", {})
    if isinstance(output, dict):
        return output.get("destination", "local")
    return "local"


def get_platforms() -> list[str]:
    """Get configured platforms (youtube, linkedin)."""
    config = get_config()
    platforms = config.get("platforms", {})
    if isinstance(platforms, list):
        return platforms
    if isinstance(platforms, dict):
        return list(platforms.keys())
    return ["youtube", "linkedin"]


def is_setup_complete() -> bool:
    """Check if the content-os setup wizard has been run."""
    root = _find_project_root()
    config_path = root / ".claude" / "content-os.local.md"
    if not config_path.exists():
        return False
    config = get_config()
    return bool(config.get("business_name"))


def get_project_root() -> Path:
    """Get the project root path."""
    return _find_project_root()
