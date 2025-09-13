# Scrap Reviews

Scrapes reviews by source (G2, Capterra, bonus: Trustpilot) for a company and date range. Outputs a single JSON file with:
- title, review_text, date
- reviewer_name (if available), rating (if available)
- plus source and company_name

## Requirements
- Python 3.12+
- A virtual environment (uv or venv)
- ScrapeOps API key in `.env` (recommended for JS-rendered pages)

`.env` (project root):
```
SCRAPEOPS_API_KEY=your_api_key
SCRAPEOPS_PROXY_ENABLED=true
# optional, increase if pages are slow to render
SCRAPEOPS_WAIT_MS=4000
```

## Install
From this folder (reviews_pulse):

```
uv venv
source .venv/bin/activate
uv pip install -e .
```

Or with pip:
```
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run (CLI)
Required:
- --source: g2 | capterra | trustpilot
- --company: company/product name (used for slug fallback and output naming)
- --start-date, --end-date: YYYY-MM-DD

Optional:
- --product-url: explicit reviews URL (most reliable)
- --product-slug: override slug if URL not provided
- --max-pages: pagination depth (default: all)
- --output: custom path to JSON
- --log-level: INFO (default) | DEBUG

Output:
- Default: `data/<source>_<company-slug>_<start>_<end>.json`

## Sample commands (worked)
G2 (NetSuite, explicit URL):
```
uv run python main.py --source g2 \
  --company "NetSuite" \
  --product-url "https://www.g2.com/products/netsuite/reviews" \
  --start-date 2024-01-01 \
  --end-date 2024-03-31 \
  --max-pages 3 \
  --log-level INFO
```

Capterra (Asana, explicit URL):
```
uv run python main.py --source capterra \
  --company "Asana" \
  --product-url "https://www.capterra.com/p/130111/Asana/reviews/" \
  --start-date 2024-01-01 \
  --end-date 2024-03-31 \
  --max-pages 10 \
  --log-level INFO
```

Trustpilot (bonus – Notion, explicit URL):
```
uv run python main.py --source trustpilot \
  --company "notion.so" \
  --product-url "https://www.trustpilot.com/review/notion.so" \
  --start-date 2024-01-01 \
  --end-date 2024-10-20 \
  --max-pages 5 \
  --log-level INFO
```

## Tips
- Prefer `--product-url` for accuracy. Slug fallback tries common patterns.
- JS-heavy pages: make sure `.env` is set and bump `SCRAPEOPS_WAIT_MS` if needed.
- Narrow date windows often require `--max-pages` > 1 to reach older reviews.

## Project layout
- `main.py`: CLI, writes one JSON file via Scrapy FEEDS.
- `scrap_reviews/`: settings, middlewares, pipelines, items, utils
- `scrap_reviews/spiders/`: `g2_reviews.py`, `capterra_reviews.py`, `trustpilot_reviews.py`
- `data/`: outputs
