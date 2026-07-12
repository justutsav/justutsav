#!/usr/bin/env python3
"""Rewrite the LIVE block in README.md.

Pulls the latest public repo pushes from the GitHub API and the newest
uploads from the @Blaze_Age YouTube RSS feed, then replaces everything
between the LIVE:START / LIVE:END markers. Stdlib only — no pip installs
in the Action.
"""

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

USER = "justutsav"
CHANNEL_ID = "UCESPKd0vzKFYew77oJgTqkQ"  # youtube.com/@Blaze_Age
README = Path(__file__).resolve().parent.parent / "README.md"
# repos that should never headline the live section (the profile repo's own
# cron commits would otherwise pin it to the top of "recently pushed")
SKIP = {USER, "activitywatch"}  # activitywatch = fork


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": f"{USER}-profile-cron"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def ago(dt: datetime) -> str:
    days = (datetime.now(timezone.utc) - dt).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days}d ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def latest_repos(n: int = 3) -> list[str]:
    data = json.loads(fetch(f"https://api.github.com/users/{USER}/repos?sort=pushed&per_page=30"))
    lines = []
    for r in data:
        if r["fork"] or r["name"] in SKIP:
            continue
        pushed = datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00"))
        desc = (r["description"] or "no description yet").strip()
        if len(desc) > 90:
            desc = desc[:87] + "…"
        lines.append(f"- [**{r['name']}**]({r['html_url']}) — {desc} · `{ago(pushed)}`")
        if len(lines) == n:
            break
    return lines


def latest_videos(n: int = 2) -> list[str]:
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(fetch(f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"))
    lines = []
    for e in root.findall("a:entry", ns)[:n]:
        title = e.find("a:title", ns).text
        link = e.find("a:link", ns).attrib["href"]
        pub = datetime.fromisoformat(e.find("a:published", ns).text)
        lines.append(f"- [{title}]({link}) · `{pub.strftime('%b %Y')}`")
    return lines


def main() -> None:
    parts = ["**⚡ recently pushed**", ""]
    parts += latest_repos()
    try:
        vids = latest_videos()
    except Exception:
        vids = []  # feed hiccup — keep the repos, skip the videos
    if vids:
        parts += ["", "**📼 latest on [@Blaze_Age](https://youtube.com/@Blaze_Age)**", ""]
        parts += vids
    ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    parts += ["", f"<sub>refreshed {ist.strftime('%d %b %Y, %H:%M')} IST · by a GitHub Actions cron, no hands involved</sub>"]

    block = "\n".join(parts)
    text = README.read_text(encoding="utf-8")
    new = re.sub(
        r"(<!--LIVE:START-->).*?(<!--LIVE:END-->)",
        rf"\1\n{block}\n\2",
        text,
        flags=re.DOTALL,
    )
    if new != text:
        README.write_text(new, encoding="utf-8")
        print("README updated")
    else:
        print("no changes")


if __name__ == "__main__":
    main()
