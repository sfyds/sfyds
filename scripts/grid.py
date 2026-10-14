"""Draw the GitHub contribution grid as SVG (light + dark), in pink."""
import json, os, urllib.error, urllib.request
from datetime import date

LOGIN = os.environ.get("LOGIN", "sfyds")
TOKEN = os.environ.get("GITHUB_TOKEN")

THEMES = {
    "pink-grid.svg": {       # light mode
        "levels": ["#eff2f5", "#ffc0e0", "#ff8cc6", "#ff4fa7", "#d6006f"],
        "text": "#59636e", "title": "#1f2328",
    },
    "pink-grid-dark.svg": {  # works on dark AND light backgrounds
        "levels": ["#8b949e33", "#f9a8d4", "#f472b6", "#db2777", "#9d174d"],
        "text": "#8b949e", "title": "#8b949e",
    },
}
LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
         "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

CELL, GAP = 10, 3
STEP = CELL + GAP
LEFT, TOP = 33, 40
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"


def fetch(year=None):
    """Last 12 months, or a whole calendar year if `year` is given."""
    query = """query($login:String!,$from:DateTime,$to:DateTime){user(login:$login){
      contributionsCollection(from:$from,to:$to){contributionYears
      contributionCalendar{totalContributions weeks{contributionDays{
      date weekday contributionCount contributionLevel}}}}}}"""
    variables = {"login": LOGIN}
    if year:
        variables["from"] = f"{year}-01-01T00:00:00Z"
        variables["to"] = f"{year}-12-31T23:59:59Z"
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    if not TOKEN:
        raise SystemExit("No token: add a GH_PAT secret (classic token, scope read:user).")
    try:
        data = json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"GitHub API error {e.code}: {e.read().decode()}")
    if "errors" in data:
        raise SystemExit(f"GitHub API error: {data['errors']}")
    coll = data["data"]["user"]["contributionsCollection"]
    cal = coll["contributionCalendar"]
    cal["years"] = coll["contributionYears"]
    cal["label"] = f"in {year}" if year else "in the last year"
    return cal


def render(cal, theme):
    weeks = cal["weeks"]
    width = LEFT + len(weeks) * STEP + 5
    height = TOP + 7 * STEP + 30
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" font-family="{FONT}">']

    total = cal["totalContributions"]
    out.append(f'<text x="0" y="14" font-size="14" fill="{theme["title"]}">'
               f'{total} contribution{"" if total == 1 else "s"} {cal["label"]}</text>')

    # month labels
    last_month, last_x = None, -100
    for i, week in enumerate(weeks):
        d = date.fromisoformat(week["contributionDays"][0]["date"])
        x = LEFT + i * STEP
        if d.month != last_month:
            if x - last_x >= 3 * STEP and i < len(weeks) - 2:
                out.append(f'<text x="{x}" y="{TOP - 7}" font-size="10" '
                           f'fill="{theme["text"]}">{d.strftime("%b")}</text>')
                last_x = x
            last_month = d.month

    # weekday labels
    for wd, name in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        out.append(f'<text x="0" y="{TOP + wd * STEP + 9}" font-size="10" '
                   f'fill="{theme["text"]}">{name}</text>')

    # cells
    for i, week in enumerate(weeks):
        for day in week["contributionDays"]:
            color = theme["levels"][LEVEL[day["contributionLevel"]]]
            x, y = LEFT + i * STEP, TOP + day["weekday"] * STEP
            n = day["contributionCount"]
            out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                       f'fill="{color}"><title>{n} contributions on {day["date"]}</title></rect>')

    # legend
    ly = TOP + 7 * STEP + 12
    lx = width - 5 * STEP - 40
    out.append(f'<text x="{lx - 30}" y="{ly + 9}" font-size="10" fill="{theme["text"]}">Less</text>')
    for k, color in enumerate(theme["levels"]):
        out.append(f'<rect x="{lx + k * STEP}" y="{ly}" width="{CELL}" height="{CELL}" rx="2" fill="{color}"/>')
    out.append(f'<text x="{lx + 5 * STEP + 4}" y="{ly + 9}" font-size="10" fill="{theme["text"]}">More</text>')

    out.append("</svg>")
    return "\n".join(out)


def save(cal, suffix=""):
    for name, theme in THEMES.items():
        path = "dist/" + name.replace(".svg", f"{suffix}.svg")
        with open(path, "w") as f:
            f.write(render(cal, theme))


if __name__ == "__main__":
    os.makedirs("dist", exist_ok=True)
    cal = fetch()
    save(cal)                                  # pink-grid-dark.svg (last year)
    print("last year:", cal["totalContributions"])
    for year in cal["years"]:                  # pink-grid-dark-2025.svg, ...
        y = fetch(year)
        save(y, f"-{year}")
        print(year, y["totalContributions"])
