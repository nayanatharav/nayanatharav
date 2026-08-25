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
    request = urllib.request.Request(
        "https://api.github.com" + path,
        headers=HEADERS
    )

    with urllib.request.urlopen(request) as response:
        return json.load(response)


def escape(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def get_repos():
    repos = []
    page = 1

    while True:
        data = api(
            f"/users/{USERNAME}/repos"
            f"?per_page=100&page={page}&type=owner"
        )

        repos.extend(data)

        if len(data) < 100:
            return repos

        page += 1


def search_count(query):
    try:
        data = api(
            "/search/issues?q=" +
            urllib.parse.quote(query)
        )

        return data.get("total_count", 0)

    except Exception:
        return 0


def make_svg(width, height, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg"
width="{width}" height="{height}"
viewBox="0 0 {width} {height}">

<rect width="100%" height="100%"
rx="12"
fill="#0d1117"
stroke="#30363d"/>

{body}

</svg>
'''


# ---------------------------------------------------------
# GET REPOSITORIES
# ---------------------------------------------------------

repos = get_repos()

since = (
    datetime.now(timezone.utc)
    - timedelta(days=365)
)


# ---------------------------------------------------------
# TOTAL STARS
# ---------------------------------------------------------

stars = sum(
    repo.get("stargazers_count", 0)
    for repo in repos
)


# ---------------------------------------------------------
# LANGUAGE USAGE
# ---------------------------------------------------------

language_bytes = Counter()

for repo in repos:

    if repo.get("fork"):
        continue

    try:

        repo_name = urllib.parse.quote(
            repo["name"],
            safe=""
        )

        languages = api(
            f"/repos/{USERNAME}/{repo_name}/languages"
        )

        language_bytes.update(languages)

    except Exception:

        continue


total_language_bytes = (
    sum(language_bytes.values()) or 1
)

top_languages = language_bytes.most_common(5)


# ---------------------------------------------------------
# COMMITS IN THE LAST YEAR
# ---------------------------------------------------------

commit_count = 0

for repo in repos:

    if repo.get("fork"):
        continue

    try:

        repo_name = urllib.parse.quote(
            repo["name"],
            safe=""
        )

        page = 1

        while True:

            commits = api(
                f"/repos/{USERNAME}/{repo_name}/commits"
                f"?author={USERNAME}"
                f"&since={since.isoformat()}"
                f"&per_page=100"
                f"&page={page}"
            )

            commit_count += len(commits)

            if len(commits) < 100:
                break

            page += 1

    except Exception:

        continue


# ---------------------------------------------------------
# PULL REQUESTS
# ---------------------------------------------------------

prs = search_count(
    f"is:pr author:{USERNAME}"
)


# ---------------------------------------------------------
# ISSUES
# ---------------------------------------------------------

issues = search_count(
    f"is:issue author:{USERNAME}"
)


# ---------------------------------------------------------
# ACTIVITY GRADE
# ---------------------------------------------------------

if commit_count >= 200:

    grade = "A"

elif commit_count >= 100:

    grade = "B"

elif commit_count >= 25:

    grade = "C"

else:

    grade = "D"


progress = min(
    100,
    max(8, commit_count // 2)
)


# ---------------------------------------------------------
# STATS DATA
# ---------------------------------------------------------

stats = [

    (
        "Total Stars Earned:",
        stars
    ),

    (
        "Total Commits (last year):",
        commit_count
    ),

    (
        "Total PRs:",
        prs
    ),

    (
        "Total Issues:",
        issues
    ),

    (
        "Public activity:",
        commit_count
    ),

]


# ---------------------------------------------------------
# CREATE STATS ROWS
# ---------------------------------------------------------

rows = []

y = 94

for label, value in stats:

    rows.append(

        f'<text x="46" y="{y}" '
        f'fill="#8b949e" '
        f'font-size="18" '
        f'font-weight="600">'
        f'{escape(label)}'
        f'</text>'

        f'<text x="430" y="{y}" '
        f'fill="#58a6ff" '
        f'font-size="18" '
        f'font-weight="700">'
        f'{value}'
        f'</text>'

    )

    y += 32


# ---------------------------------------------------------
# ACTIVITY CIRCLE
# ---------------------------------------------------------

cx = 690
cy = 145
radius = 55

circumference = (
    2 * 3.1415926535 * radius
)

dash = (
    circumference * progress / 100
)


# ---------------------------------------------------------
# STATS SVG
# ---------------------------------------------------------

stats_body = f'''

<text
x="46"
y="44"
fill="#58a6ff"
font-size="24"
font-weight="700">

📊 {escape(USERNAME)}'s GitHub Stats

</text>


{''.join(rows)}


<circle
cx="{cx}"
cy="{cy}"
r="{radius}"
fill="none"
stroke="#21262d"
stroke-width="12"
/>


<circle
cx="{cx}"
cy="{cy}"
r="{radius}"
fill="none"
stroke="#58a6ff"
stroke-width="12"
stroke-linecap="round"
stroke-dasharray="{dash:.1f} {circumference:.1f}"
transform="rotate(-90 {cx} {cy})"
/>


<text
x="{cx}"
y="{cy + 12}"
text-anchor="middle"
fill="#8b949e"
font-size="34"
font-weight="800">

{grade}

</text>

'''


(OUT / "github-stats.svg").write_text(
    make_svg(
        850,
        235,
        stats_body
    ),
    encoding="utf-8"
)


# ---------------------------------------------------------
# LANGUAGE CARD
# ---------------------------------------------------------

palette = [
    "#58a6ff",
    "#3fb950",
    "#d29922",
    "#bc8cff",
    "#f778ba"
]


bar_x = 46
bar_y = 78
bar_w = 758
bar_h = 16


language_parts = [

    '''
    <text
    x="46"
    y="44"
    fill="#58a6ff"
    font-size="24"
    font-weight="700">

    Most Used Languages

    </text>
    '''

]


# ---------------------------------------------------------
# LANGUAGE BAR
# ---------------------------------------------------------

x = bar_x

for i, (language, amount) in enumerate(
    top_languages
):

    width = (
        bar_w
        * amount
        / total_language_bytes
    )

    language_parts.append(

        f'''
        <rect
        x="{x:.1f}"
        y="{bar_y}"
        width="{width:.1f}"
        height="{bar_h}"
        fill="{palette[i % len(palette)]}"
        />
        '''

    )

    x += width


# ---------------------------------------------------------
# LANGUAGE LABELS
# ---------------------------------------------------------

for i, (language, amount) in enumerate(
    top_languages
):

    column = i % 2
    row = i // 2

    label_x = (
        70 + column * 370
    )

    label_y = (
        135 + row * 34
    )

    percentage = (
        amount
        / total_language_bytes
        * 100
    )

    language_parts.append(

        f'''
        <circle
        cx="{label_x}"
        cy="{label_y - 5}"
        r="7"
        fill="{palette[i % len(palette)]}"
        />

        <text
        x="{label_x + 14}"
        y="{label_y}"
        fill="#8b949e"
        font-size="16">

        {escape(language)}
        {percentage:.1f}%

        </text>
        '''

    )


# ---------------------------------------------------------
# SAVE LANGUAGE SVG
# ---------------------------------------------------------

(OUT / "github-languages.svg").write_text(

    make_svg(
        850,
        235,
        "\n".join(language_parts)
    ),

    encoding="utf-8"

)


print(
    "Generated github-stats.svg "
    "and github-languages.svg"
)
