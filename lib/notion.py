"""
Notion API client for content-os plugin.

Generalized version — reads NOTION_TOKEN and database ID from config,
not hardcoded. Optional integration: if Notion is not configured, all
functions return gracefully without errors.

Usage:
    from lib.notion import create_content_page, upload_image_to_page

    page = create_content_page("My Title", "Planning", "## Outline\n- Point 1")
    upload_image_to_page(page["id"], "/path/to/image.png")
"""

import json
import logging
import mimetypes
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

try:
    import requests
except ImportError:
    requests = None

# ---------------------------------------------------------------------------
# Config loading (lazy — avoid circular imports with config.py)
# ---------------------------------------------------------------------------

_NOTION_TOKEN: str | None = None
_DATABASE_ID: str | None = None
_HEADERS: dict | None = None

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

log = logging.getLogger("content-os.notion")


def _ensure_config():
    """Load Notion config on first use."""
    global _NOTION_TOKEN, _DATABASE_ID, _HEADERS

    if _HEADERS is not None:
        return

    # Try loading from config module
    try:
        from lib.config import get_key, get_config
        _NOTION_TOKEN = get_key("notion")
        config = get_config()
        output = config.get("output", {})
        if isinstance(output, dict):
            _DATABASE_ID = output.get("notion_database_id")
    except ImportError:
        pass

    # Fallback to environment
    if not _NOTION_TOKEN:
        _NOTION_TOKEN = (
            os.environ.get("NOTION_TOKEN")
            or os.environ.get("NOTION_API_KEY")
            or os.environ.get("NOTION_INTEGRATION_TOKEN")
        )

    if not _DATABASE_ID:
        _DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

    if _NOTION_TOKEN:
        _HEADERS = {
            "Authorization": f"Bearer {_NOTION_TOKEN}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }


def is_configured() -> bool:
    """Check if Notion integration is configured."""
    _ensure_config()
    return bool(_NOTION_TOKEN and _DATABASE_ID)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _request(method: str, url: str, headers: dict | None = None, _retries: int = 3, **kwargs) -> dict:
    """Make an HTTP request to Notion API with error handling and 429 retry."""
    if requests is None:
        raise RuntimeError("requests library not installed. Run: pip install requests")

    _ensure_config()
    hdrs = headers or _HEADERS
    if not hdrs:
        raise RuntimeError("Notion not configured. Run /content-setup or set NOTION_TOKEN in .env")

    for attempt in range(_retries):
        resp = requests.request(method, url, headers=hdrs, **kwargs)
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", 1))
            log.warning("Notion rate limited, retrying in %.1fs (attempt %d/%d)",
                        retry_after, attempt + 1, _retries)
            time.sleep(retry_after)
            continue
        if not resp.ok:
            log.error("Notion API %s %s → %s: %s", method, url, resp.status_code, resp.text)
            resp.raise_for_status()
        if resp.status_code == 204 or not resp.text:
            return {}
        return resp.json()
    resp.raise_for_status()
    return {}


def _markdown_to_blocks(markdown: str) -> list[dict]:
    """Convert markdown text into Notion block children."""
    blocks = []
    lines = markdown.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Code blocks
        if stripped.startswith("```"):
            language = stripped[3:].strip() or "plain text"
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1
            blocks.append({
                "object": "block", "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": "\n".join(code_lines)}}],
                    "language": language,
                },
            })
            continue

        if stripped.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3",
                           "heading_3": {"rich_text": _parse_inline(stripped[4:])}})
        elif stripped.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2",
                           "heading_2": {"rich_text": _parse_inline(stripped[3:])}})
        elif stripped.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1",
                           "heading_1": {"rich_text": _parse_inline(stripped[2:])}})
        elif stripped in ("---", "***", "___"):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        elif stripped.startswith("- ") or stripped.startswith("* "):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                           "bulleted_list_item": {"rich_text": _parse_inline(stripped[2:])}})
        elif re.match(r"^\d{1,2}[\.\)] ", stripped):
            text_start = stripped.index(" ") + 1
            blocks.append({"object": "block", "type": "numbered_list_item",
                           "numbered_list_item": {"rich_text": _parse_inline(stripped[text_start:])}})
        elif stripped.startswith("> "):
            blocks.append({"object": "block", "type": "quote",
                           "quote": {"rich_text": _parse_inline(stripped[2:])}})
        else:
            blocks.append({"object": "block", "type": "paragraph",
                           "paragraph": {"rich_text": _parse_inline(stripped)}})
        i += 1

    return blocks


def _parse_inline(text: str) -> list[dict]:
    """Parse bold and code inline formatting."""
    segments = []
    pattern = r'(\*\*(.+?)\*\*|`(.+?)`)'
    last_end = 0

    for match in re.finditer(pattern, text):
        if match.start() > last_end:
            plain = text[last_end:match.start()]
            if plain:
                segments.append({"type": "text", "text": {"content": plain}})
        if match.group(2):
            segments.append({"type": "text", "text": {"content": match.group(2)},
                             "annotations": {"bold": True}})
        elif match.group(3):
            segments.append({"type": "text", "text": {"content": match.group(3)},
                             "annotations": {"code": True}})
        last_end = match.end()

    remaining = text[last_end:]
    if remaining:
        segments.append({"type": "text", "text": {"content": remaining}})
    if not segments:
        segments.append({"type": "text", "text": {"content": text}})

    return segments


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Valid property values — users can customize these via config
VALID_STATUSES = ["Planning", "In Progress", "Ready To Record",
                  "Ready To Post", "Awaiting Review", "Complete"]
VALID_PRIORITIES = ["Urgent", "High", "Low"]


def create_content_page(
    title: str,
    status: str = "Planning",
    body_markdown: str = "",
    metadata: dict | None = None,
) -> dict:
    """Create a new page in the configured Notion database."""
    _ensure_config()
    if not _DATABASE_ID:
        raise RuntimeError("Notion database ID not configured. Set it in .claude/content-os.local.md")

    meta = metadata or {}
    props: dict[str, Any] = {
        "Name": {"title": [{"type": "text", "text": {"content": title}}]},
    }
    if status:
        props["Status"] = {"status": {"name": status}}
    if meta.get("priority"):
        props["Priority"] = {"select": {"name": meta["priority"]}}
    if meta.get("tags"):
        props["Tags"] = {"multi_select": [{"name": t} for t in meta["tags"]]}

    children = _markdown_to_blocks(body_markdown) if body_markdown else []

    payload: dict[str, Any] = {
        "parent": {"database_id": _DATABASE_ID},
        "properties": props,
    }
    if children:
        payload["children"] = children

    result = _request("POST", f"{BASE_URL}/pages", json=payload)
    page_id = result["id"]
    page_url = result.get("url", f"https://notion.so/{page_id.replace('-', '')}")

    log.info("Created page: %s → %s", title, page_url)
    return {"id": page_id, "url": page_url}


def update_content_page(page_id: str, updates: dict) -> bool:
    """Update properties and/or content of an existing page."""
    try:
        prop_keys = {"status", "priority", "tags", "title"}
        if prop_keys & updates.keys():
            props: dict[str, Any] = {}
            if updates.get("title"):
                props["Name"] = {"title": [{"type": "text", "text": {"content": updates["title"]}}]}
            if updates.get("status"):
                props["Status"] = {"status": {"name": updates["status"]}}
            if updates.get("priority"):
                props["Priority"] = {"select": {"name": updates["priority"]}}
            if updates.get("tags"):
                props["Tags"] = {"multi_select": [{"name": t} for t in updates["tags"]]}
            if props:
                _request("PATCH", f"{BASE_URL}/pages/{page_id}", json={"properties": props})

        if updates.get("body_markdown"):
            existing = _request("GET", f"{BASE_URL}/blocks/{page_id}/children")
            for block in existing.get("results", []):
                try:
                    _request("DELETE", f"{BASE_URL}/blocks/{block['id']}")
                except Exception:
                    pass
            new_blocks = _markdown_to_blocks(updates["body_markdown"])
            if new_blocks:
                _request("PATCH", f"{BASE_URL}/blocks/{page_id}/children",
                         json={"children": new_blocks})
        return True
    except Exception as exc:
        log.error("Failed to update page %s: %s", page_id, exc)
        return False


def _upload_file_to_notion(page_id: str, file_path: str) -> str:
    """Upload a file via Notion's 3-step file upload API."""
    _ensure_config()
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    filename = path.name
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    upload_meta = _request("POST", f"{BASE_URL}/file_uploads", json={
        "filename": filename, "content_type": content_type, "mode": "single_part",
    })
    file_upload_id = upload_meta["id"]

    upload_headers = {
        "Authorization": f"Bearer {_NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
    }
    with open(path, "rb") as f:
        _request("POST", f"{BASE_URL}/file_uploads/{file_upload_id}/send",
                 headers=upload_headers, files={"file": (filename, f, content_type)})

    return file_upload_id


def upload_image_to_page(page_id: str, image_path: str, caption: str | None = None) -> str:
    """Upload an image and append it as a block on the page."""
    file_upload_id = _upload_file_to_notion(page_id, image_path)

    image_block: dict[str, Any] = {
        "object": "block", "type": "image",
        "image": {"type": "file_upload", "file_upload": {"id": file_upload_id}},
    }
    if caption:
        image_block["image"]["caption"] = [{"type": "text", "text": {"content": caption}}]

    _request("PATCH", f"{BASE_URL}/blocks/{page_id}/children",
             json={"children": [image_block]})

    try:
        _request("PATCH", f"{BASE_URL}/pages/{page_id}", json={
            "properties": {"image": {"files": [
                {"type": "file_upload", "file_upload": {"id": file_upload_id}, "name": Path(image_path).name}
            ]}}
        })
    except Exception:
        pass

    return file_upload_id


def upload_pdf_to_page(page_id: str, pdf_path: str, caption: str | None = None) -> str:
    """Upload a PDF and append it as a block on the page."""
    file_upload_id = _upload_file_to_notion(page_id, pdf_path)

    pdf_block: dict[str, Any] = {
        "object": "block", "type": "pdf",
        "pdf": {"type": "file_upload", "file_upload": {"id": file_upload_id}},
    }
    if caption:
        pdf_block["pdf"]["caption"] = [{"type": "text", "text": {"content": caption}}]

    _request("PATCH", f"{BASE_URL}/blocks/{page_id}/children",
             json={"children": [pdf_block]})
    return file_upload_id


def find_content_page(title: str) -> Optional[str]:
    """Search the database for a page by title. Returns page ID or None."""
    _ensure_config()
    if not _DATABASE_ID:
        return None

    payload = {"filter": {"property": "Name", "title": {"equals": title}}}
    result = _request("POST", f"{BASE_URL}/databases/{_DATABASE_ID}/query", json=payload)
    results = result.get("results", [])
    return results[0]["id"] if results else None
