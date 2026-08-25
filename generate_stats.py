#!/usr/bin/env python3
import json
import os
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

USERNAME = "nayanatharav"
OUT = Path(__file__).resolve().parent
TOKEN = os.environ.get("GITHUB_TOKEN")

if not TOKEN:
    raise SystemExit("GITHUB_TOKEN is required")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "nayanatharav-profile-stats",
}

def api(path):
    req = urllib.request.Request("https://api.github.com" + path, headers=HEADERS)
    with urllib.request.urlopen(req) as response:
        return json.load(response)

def escape(value):
    return (str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))

def get_repos():
    repos = []
    page = 1
    while True:
        data = api(f"/users/{USERNAME}/repos?per_page=100&page={page}&type=owner")
        repos.extend(data)
        if len(data) < 100:
            return repos
        page += 1

def search_count(query):
    try:
        data = api("/search/issues?q=" + urllib.parse.quote(query))
        return data.get("total_count", 0)
    except Exception:
        return 0

def make_svg(width, height, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" rx="12" fill="#0d1117" stroke="#30363d"/>
{body}
</svg>
'''

repos = get_repos()
since = datetime.now(timezone.utc) - timedelta(days=365)

stars = sum(r.get("stargazers_count", 0) for r in repos)

# Repository language usage, weighted by bytes.
language_bytes = Counter()
for repo in repos:
    if repo.get("fork"):
        continue
    try:
        name = urllib.parse.quote(repo["name"], safe="")
        language_bytes.update(api(f"/repos/{USERNAME}/{name}/languages"))
    except Exception:
        pass

total_language_bytes = sum(language_bytes.values()) or 1
top_languages = language_bytes.most_common(5)

# Count public PushEvent commits visible through the Events API.
commit_count = 0
for page in range(1, 11):
    try:
        events = api(f"/users/{USERNAME}/events/public?per_page=100&page={page}")
    except Exception:
        break
    if not events:
        break

    stop = False
    for event in events:
        created = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
        if created < since:
            stop = True
            continue
        if event["type"] == "PushEvent":
            commit_count += len(event.get("payload", {}).get("commits", []))

    if stop:
        break

prs = search_count(f"is:pr author:{USERNAME}")
issues = search_count(f"is:issue author:{USERNAME}")

grade = "A" if commit_count >= 200 else "B" if commit_count >= 100 else "C" if commit_count >= 25 else "D"
progress = min(100, max(8, commit_count // 2))

stats = [
    ("Total Stars Earned:", stars),
    ("Total Commits (last year):", commit_count),
    ("Total PRs:", prs),
    ("Total Issues:", issues),
    ("Public activity:", commit_count),
]

rows = []
y = 94
for label, value in stats:
    rows.append(
        f'<text x="46" y="{y}" fill="#8b949e" font-size="18" font-weight="600">{escape(label)}</text>'
        f'<text x="430" y="{y}" fill="#58a6ff" font-size="18" font-weight="700">{value}</text>'
    )
    y += 32

cx, cy, radius = 690, 145, 55
circ = 2 * 3.1415926535 * radius
dash = circ * progress / 100

stats_body = f'''
<text x="46" y="44" fill="#58a6ff" font-size="24" font-weight="700">📊 {escape(USERNAME)}'s GitHub Stats</text>
{''.join(rows)}
<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="#21262d" stroke-width="12"/>
<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="#58a6ff" stroke-width="12"
 stroke-linecap="round" stroke-dasharray="{dash:.1f} {circ:.1f}"
 transform="rotate(-90 {cx} {cy})"/>
<text x="{cx}" y="{cy+12}" text-anchor="middle" fill="#8b949e" font-size="34" font-weight="800">{grade}</text>
'''

(OUT / "github-stats.svg").write_text(
    make_svg(850, 235, stats_body), encoding="utf-8"
)

palette = ["#58a6ff", "#3fb950", "#d29922", "#bc8cff", "#f778ba"]
bar_x, bar_y, bar_w, bar_h = 46, 78, 758, 16

language_parts = [
    '<text x="46" y="44" fill="#58a6ff" font-size="24" font-weight="700">Most Used Languages</text>'
]

x = bar_x
for i, (lang, amount) in enumerate(top_languages):
    width = bar_w * amount / total_language_bytes
    language_parts.append(
        f'<rect x="{x:.1f}" y="{bar_y}" width="{width:.1f}" height="{bar_h}" fill="{palette[i % len(palette)]}"/>'
    )
    x += width

for i, (lang, amount) in enumerate(top_languages):
    col = i % 2
    row = i // 2
    lx = 70 + col * 370
    ly = 135 + row * 34
    pct = amount / total_language_bytes * 100
    language_parts.append(
        f'<circle cx="{lx}" cy="{ly-5}" r="7" fill="{palette[i % len(palette)]}"/>'
        f'<text x="{lx+14}" y="{ly}" fill="#8b949e" font-size="16">{escape(lang)} {pct:.1f}%</text>'
    )

(OUT / "github-languages.svg").write_text(
    make_svg(850, 235, "\n".join(language_parts)), encoding="utf-8"
)

print("Generated github-stats.svg and github-languages.svg")
