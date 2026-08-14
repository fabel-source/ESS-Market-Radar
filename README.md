# ESS Market Radar

A self-updating maritime ESS intelligence dashboard. Every Friday at 07:00 UTC a GitHub Actions workflow calls the Anthropic API (with live web search), generates a fresh 10-slide briefing, and publishes it to GitHub Pages — automatically.

---

## How it works

```
GitHub Actions (every Friday 07:00 UTC)
    → fetch_briefing.py calls Anthropic API + web search
    → saves structured JSON to data/briefing.json
    → commits and pushes to repo
GitHub Pages serves docs/index.html
    → dashboard reads data/briefing.json and renders all 10 slides
```

---

## Setup (≈15 minutes)

### 1. Fork or create a new GitHub repository

Go to [github.com](https://github.com) → **New repository**.  
Name it `ess-market-radar` (or anything you like). Set it to **Public** (required for free GitHub Pages).

Upload all files from this package maintaining the folder structure:
```
.github/workflows/weekly_briefing.yml
data/briefing.json          ← sample data so the site works immediately
docs/index.html
fetch_briefing.py
README.md
```

### 2. Add your Anthropic API key as a secret

In your GitHub repo:  
**Settings → Secrets and variables → Actions → New repository secret**

- Name: `ANTHROPIC_API_KEY`
- Value: your Anthropic API key (get one at [console.anthropic.com](https://console.anthropic.com))

### 3. Enable GitHub Pages

In your GitHub repo:  
**Settings → Pages → Source: Deploy from a branch → Branch: `main` / Folder: `/docs`**

Click **Save**. Your dashboard will be live at:  
`https://YOUR-USERNAME.github.io/ess-market-radar/`

(Takes 1–2 minutes to go live the first time.)

### 4. Run your first briefing manually

Go to **Actions → ESS Market Radar — Weekly Briefing → Run workflow → Run workflow**

This triggers an immediate fetch. Watch the workflow log — it takes about 60–90 seconds.  
When complete, refresh your GitHub Pages URL to see the live dashboard.

After this, the workflow runs automatically every **Friday at 07:00 UTC**.

---

## Local development & testing

```bash
# Install dependency
pip install anthropic

# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# Fetch a fresh briefing (takes ~60 seconds, uses web search)
python fetch_briefing.py

# Open the dashboard locally
open docs/index.html
# or: python -m http.server 8000 → http://localhost:8000/docs/
```

---

## File structure

```
ess-market-radar/
├── .github/
│   └── workflows/
│       └── weekly_briefing.yml   # GitHub Actions — runs every Friday
├── data/
│   ├── briefing.json             # Latest briefing (overwritten weekly)
│   └── briefing_YYYY-MM-DD.json  # Dated archive (one per week, auto-created)
├── docs/
│   └── index.html                # Dashboard — served by GitHub Pages
├── fetch_briefing.py             # Script that calls Anthropic API
└── README.md
```

---

## Customising the briefing

The intelligence focus is defined by two strings at the top of `fetch_briefing.py`:

- **`SYSTEM_PROMPT`** — the analyst persona and scope (companies to track, vessel types, chemistry, regulatory bodies). Edit this to change what the analyst focuses on.
- **`USER_PROMPT`** — the weekly instruction sent to the model. Edit this to change search terms or emphasis.

---

## Schedule

The workflow runs every **Friday at 07:00 UTC** (configured in `.github/workflows/weekly_briefing.yml`).

To change the day/time, edit the cron expression:
```yaml
- cron: "0 7 * * 5"   # minute hour day month weekday (5 = Friday)
```

Examples:
- Monday 06:00 UTC: `"0 6 * * 1"`
- Wednesday 08:30 UTC: `"30 8 * * 3"`

---

## Cost

Each weekly run uses approximately **8,000–12,000 tokens** (including web search tool calls).  
At current Anthropic pricing for Claude Sonnet, this is roughly **$0.04–0.08 per weekly run** (~$2–4/year).

---

## Briefing archive

Every run saves a dated copy to `data/briefing_YYYY-MM-DD.json` alongside the current `briefing.json`. These are committed to the repo, giving you a full version-controlled history of every weekly briefing.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Workflow fails with auth error | Check `ANTHROPIC_API_KEY` secret is set correctly in repo Settings |
| Dashboard shows "Could not load briefing data" | Run the workflow once manually, or run `fetch_briefing.py` locally and commit `data/briefing.json` |
| GitHub Pages shows 404 | Check Pages is set to `/docs` folder, not root. Wait 2 minutes after enabling. |
| Charts don't render | Open browser console — likely a JSON parse error. Run `python -c "import json; json.load(open('data/briefing.json'))"` to validate. |
