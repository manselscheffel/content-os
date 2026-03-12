#!/usr/bin/env python3
"""Extract timestamps from a YouTube transcript.

Reads a transcript file (text with timing info) and identifies topic transitions
to generate a timestamp list for the video description.

Usage:
    python3 extract_timestamps.py --transcript-file .tmp/transcript.txt
    python3 extract_timestamps.py --transcript-text "raw transcript text"

Output: JSON with timestamps array.
"""

import argparse
import json
import re
import sys


def parse_timed_transcript(text):
    """Parse transcript with embedded timestamps like [00:00] or (0:00)."""
    # Match patterns like [00:00], [0:00:00], (00:00), timestamps at start of lines
    pattern = r'[\[\(]?(\d{1,2}:?\d{2}(?::\d{2})?)[\]\)]?\s*[-–]?\s*(.*?)(?=[\[\(]?\d{1,2}:?\d{2}|\Z)'
    matches = re.findall(pattern, text, re.DOTALL)

    segments = []
    for time_str, content in matches:
        content = content.strip()
        if content and len(content) > 10:  # Skip very short segments
            segments.append({
                "time": normalize_time(time_str),
                "text": content[:500],  # Cap segment length
            })

    return segments


def normalize_time(time_str):
    """Normalize time string to H:MM:SS or M:SS format."""
    parts = time_str.split(":")
    if len(parts) == 2:
        m, s = int(parts[0]), int(parts[1])
        if m >= 60:
            h = m // 60
            m = m % 60
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"
    elif len(parts) == 3:
        h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        return f"{h}:{m:02d}:{s:02d}"
    return time_str


def parse_plain_transcript(text):
    """Parse transcript without timestamps — split by topic shifts."""
    # Split into sentences/paragraphs
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    segments = []
    for i, para in enumerate(paragraphs):
        if len(para) > 20:  # Skip very short lines
            segments.append({
                "index": i,
                "text": para[:500],
            })

    return segments


def main():
    parser = argparse.ArgumentParser(description="Extract timestamps from transcript")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--transcript-file", help="Path to transcript file")
    group.add_argument("--transcript-text", help="Raw transcript text")

    args = parser.parse_args()

    if args.transcript_file:
        try:
            with open(args.transcript_file) as f:
                text = f.read()
        except FileNotFoundError:
            print(json.dumps({"success": False, "error": f"File not found: {args.transcript_file}"}))
            sys.exit(1)
    else:
        text = args.transcript_text

    if not text or len(text.strip()) < 50:
        print(json.dumps({"success": False, "error": "Transcript too short or empty"}))
        sys.exit(1)

    # Try timed transcript first
    has_times = bool(re.search(r'[\[\(]?\d{1,2}:\d{2}', text))

    if has_times:
        segments = parse_timed_transcript(text)
        mode = "timed"
    else:
        segments = parse_plain_transcript(text)
        mode = "plain"

    output = {
        "success": True,
        "mode": mode,
        "segment_count": len(segments),
        "segments": segments,
        "note": "Review and adjust section names. For plain transcripts, "
                "Claude should assign timestamps based on video duration and topic flow."
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
