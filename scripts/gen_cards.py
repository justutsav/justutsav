#!/usr/bin/env python3
"""Render a self-contained stats card SVG from live GitHub data.

Everything third-party stat services gave us (totals, streak, stars) but as a
single SVG committed into the repo — no external host to 404, and painted in
the site palette so it reads on both GitHub themes. Stdlib only.
"""

import json
import subprocess
from datetime import date, datetime
from pathlib import Path

USER = "justutsav"
OUT = Path(__file__).resolve().parent.parent / "assets" / "card-stats.svg"

# palette (site theme.css)
PAPER, INK, SOFT = "#0e0d0b", "#f2ede2", "#a49a88"
ORANGE, BLUE, PINK = "#ff5a24", "#5b8cff", "#ffa7c9"
WELL, LINE = "#191713", "#2a2622"

QUERY = """
{ user(login:"%s") {
    followers { totalCount }
    contributionsCollection {
      contributionCalendar { totalContributions
        weeks { contributionDays { date contributionCount } } } }
    repositories(first:100, ownerAffiliations:OWNER, isFork:false) {
      totalCount nodes { stargazerCount } }
} }""" % USER


def gql() -> dict:
    # shell out to the gh CLI — preinstalled locally and in Actions, and it
    # already carries an authenticated token so there's nothing to wire up
    out = subprocess.check_output(["gh", "api", "graphql", "-f", f"query={QUERY}"], timeout=40)
    return json.loads(out)["data"]["user"]


def streaks(days: list[tuple[str, int]]) -> tuple[int, int]:
    """(current, longest) consecutive active days. Today with 0 doesn't break
    the current streak — the day isn't over yet."""
    days.sort()
    longest = run = 0
    for _, c in days:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    cur = 0
    today = date.today()
    for d, c in reversed(days):
        dd = datetime.strptime(d, "%Y-%m-%d").date()
        if dd == today and c == 0:
            continue  # grace for the current, unfinished day
        if c > 0:
            cur += 1
        else:
            break
    return cur, longest


def main() -> None:
    u = gql()
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [(d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]]
    cur, longest = streaks(days)
    total = cal["totalContributions"]
    stars = sum(n["stargazerCount"] for n in u["repositories"]["nodes"])
    repos = u["repositories"]["totalCount"]
    followers = u["followers"]["totalCount"]

    def stat(x, y, num, label, color=INK):
        return (
            f'<text x="{x}" y="{y}" font-family="Arial Black,Arial,sans-serif" '
            f'font-weight="900" font-size="30" fill="{color}">{num}</text>'
            f'<text x="{x}" y="{y+20}" font-family="Courier New,monospace" font-size="11" '
            f'letter-spacing="1.5" fill="{SOFT}">{label}</text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" role="img" aria-label="GitHub stats">
  <rect width="495" height="195" rx="10" fill="{PAPER}" stroke="{LINE}"/>
  <text x="26" y="38" font-family="Courier New,monospace" font-size="13" letter-spacing="3" fill="{ORANGE}">UTSAV · BY THE NUMBERS</text>
  <line x1="26" y1="52" x2="300" y2="52" stroke="{LINE}"/>
  {stat(26, 100, total, "CONTRIBS / YR", ORANGE)}
  {stat(195, 100, stars, "TOTAL STARS")}
  {stat(26, 165, repos, "REPOS SHIPPED")}
  {stat(195, 165, followers, "FOLLOWERS")}

  <!-- current-streak ring -->
  <g transform="translate(410,97)">
    <circle r="58" fill="{WELL}"/>
    <circle r="58" fill="none" stroke="{LINE}"/>
    <circle r="47" fill="none" stroke="{ORANGE}" stroke-width="3" stroke-dasharray="7 5" opacity="0.9">
      <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="16s" repeatCount="indefinite"/>
    </circle>
    <text y="-8" text-anchor="middle" font-family="Arial Black,Arial,sans-serif" font-weight="900" font-size="34" fill="{INK}">{cur}</text>
    <text y="14" text-anchor="middle" font-family="Courier New,monospace" font-size="10" letter-spacing="1.5" fill="{ORANGE}">DAY STREAK</text>
    <text y="32" text-anchor="middle" font-family="Courier New,monospace" font-size="9" fill="{SOFT}">best {longest}</text>
  </g>
</svg>
"""
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    print(f"card written: {total} contribs, {cur}/{longest} streak, {stars}★, {repos} repos")


if __name__ == "__main__":
    main()
