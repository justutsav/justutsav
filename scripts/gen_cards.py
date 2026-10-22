#!/usr/bin/env python3
"""Render a self-contained stats card SVG from live GitHub data.

Everything third-party stat services gave us (totals, streak, stars) but as a
single SVG committed into the repo — no external host to 404, and painted in
the site palette so it reads on both GitHub themes. Stdlib only.
"""

import json
import re
import subprocess
from datetime import date, datetime
from pathlib import Path

USER = "justutsav"
OUT = Path(__file__).resolve().parent.parent / "assets" / "card-stats.svg"
README = OUT.parent.parent / "README.md"

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


def box(x0, y0, z0, x1, y1, z1, bottom=True) -> list[str]:
    """ASCII STL facets for an axis-aligned box (bottom face optional)."""
    v = lambda x, y, z: f"vertex {x:g} {y:g} {z:g}"
    quads = [  # normal, four corners counter-clockwise seen from outside
        ((0, 0, 1), [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]),
        ((0, -1, 0), [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]),
        ((0, 1, 0), [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)]),
        ((-1, 0, 0), [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)]),
        ((1, 0, 0), [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)]),
    ]
    if bottom:
        quads.append(((0, 0, -1), [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)]))
    out = []
    for n, (a, b, c, d) in quads:
        for tri in ((a, b, c), (a, c, d)):
            out.append(f"facet normal {n[0]} {n[1]} {n[2]}\nouter loop\n"
                       + "\n".join(v(*p) for p in tri) + "\nendloop\nendfacet")
    return out


def skyline_stl(days: list[tuple[str, int]]) -> str:
    """Last year of contributions as a 3D city: one tower per active day,
    weeks along x, weekdays along y, sqrt-scaled height so one busy day
    doesn't flatten the rest. GitHub renders ```stl blocks as a 3D viewer."""
    start = datetime.strptime(days[0][0], "%Y-%m-%d").date()
    start_sun = start.toordinal() - (start.weekday() + 1) % 7
    peak = max(c for _, c in days) or 1
    facets, weeks = [], 0
    for d, c in days:
        dd = datetime.strptime(d, "%Y-%m-%d").date()
        wk, wd = (dd.toordinal() - start_sun) // 7, (dd.weekday() + 1) % 7
        weeks = max(weeks, wk + 1)
        if c:
            h = round(0.4 + 9 * (c / peak) ** 0.5, 1)
            facets += box(wk + 0.1, 6 - wd + 0.1, 0, wk + 0.9, 6 - wd + 0.9, h, bottom=False)
    facets += box(-1, -1, -1, weeks + 1, 8, 0)  # plinth
    return "solid skyline\n" + "\n".join(facets) + "\nendsolid skyline"


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
  <text x="26" y="38" font-family="Courier New,monospace" font-size="13" letter-spacing="3" fill="{ORANGE}">UTSAV · ON GITHUB</text>
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
    stl = skyline_stl(days)
    assert stl.count("facet normal") == 10 * sum(1 for _, c in days if c) + 12
    text = README.read_text(encoding="utf-8")
    README.write_text(re.sub(r"(<!--SKYLINE:START-->).*?(<!--SKYLINE:END-->)",
                             lambda m: f"{m[1]}\n```stl\n{stl}\n```\n{m[2]}", text, flags=re.DOTALL),
                      encoding="utf-8")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    print(f"card written: {total} contribs, {cur}/{longest} streak, {stars}★, {repos} repos")


if __name__ == "__main__":
    main()
