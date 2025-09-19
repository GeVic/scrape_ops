#!/usr/bin/env python3
import argparse
import os
from datetime import datetime
from typing import Optional

from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings

from scrap_reviews import settings as project_settings
from scrap_reviews.utils import slugify, parse_date


SPIDER_BY_SOURCE = {
    "g2": "g2_reviews",
    "capterra": "capterra_reviews",
    "trustpilot": "trustpilot_reviews",
}


def build_output_path(
    source: str,
    company: str,
    start: Optional[str],
    end: Optional[str],
    output: Optional[str],
) -> str:
    if output:
        out_path = output
    else:
        root = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(root, "data")
        os.makedirs(data_dir, exist_ok=True)
        slug = slugify(company) or "company"
        start_s = start or "start"
        end_s = end or "end"
        out_path = os.path.join(
            data_dir,
            f"{source}_{slug}_{start_s}_{end_s}.json",
        )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    return out_path


def validate_dates(
    start: Optional[str], end: Optional[str]
) -> tuple[Optional[str], Optional[str]]:
    s = parse_date(start) if start else None
    e = parse_date(end) if end else None
    if s and e and s > e:
        raise SystemExit(f"Invalid date range: start_date ({s}) > end_date ({e})")
    return s, e


def run(
    source: str,
    company_name: str,
    start_date: Optional[str],
    end_date: Optional[str],
    product_url: Optional[str],
    product_slug: Optional[str],
    output: Optional[str],
    max_pages: Optional[int],
    log_level: str,
):
    spider_name = SPIDER_BY_SOURCE.get(source.lower())
    if not spider_name:
        raise SystemExit(
            f"Unsupported source: {source}. Choose from: {', '.join(SPIDER_BY_SOURCE)}"
        )

    start_iso, end_iso = validate_dates(start_date, end_date)
    out_path = build_output_path(source, company_name, start_iso, end_iso, output)

    s = Settings()
    s.setmodule(project_settings)
    s.set("LOG_LEVEL", log_level)
    s.set(
        "FEEDS",
        {
            out_path: {
                "format": "json",
                "encoding": "utf-8",
                "indent": 2,
                "overwrite": True,
            }
        },
    )
    s.set(
        "ITEM_PIPELINES",
        {
            "scrap_reviews.pipelines.DataValidationPipeline": 300,
            "scrap_reviews.pipelines.DuplicatesPipeline": 400,
            "scrap_reviews.pipelines.LoggingPipeline": 500,
        },
    )

    process = CrawlerProcess(settings=s)
    process.crawl(
        spider_name,
        company_name=company_name,
        start_date=start_iso,
        end_date=end_iso,
        product_url=product_url,
        product_slug=product_slug,
        max_pages=max_pages,
    )
    process.start()

    print(f"Wrote: {out_path}")


def main():
    parser = argparse.ArgumentParser(
        prog="scrap-reviews", description="Scrape product reviews into JSON."
    )
    parser.add_argument(
        "--source",
        "-S",
        required=True,
        choices=sorted(SPIDER_BY_SOURCE.keys()),
        help="g2, capterra, trustpilot",
    )
    parser.add_argument("--company", "-c", required=True, help="Company/Product name")
    parser.add_argument(
        "--start-date", "-s", required=True, help="Start date (e.g. 2024-01-01)"
    )
    parser.add_argument(
        "--end-date", "-e", required=True, help="End date (e.g. 2024-12-31)"
    )
    parser.add_argument("--product-url", help="Explicit product reviews URL")
    parser.add_argument("--product-slug", help="Override slug if URL not provided")
    parser.add_argument(
        "--output",
        "-o",
        help="Output JSON path (default: data/<source>_<company>_<start>_<end>.json)",
    )
    parser.add_argument("--max-pages", type=int, help="Limit number of pages to crawl")
    parser.add_argument(
        "--log-level", default="INFO", help="Scrapy log level (default: INFO)"
    )
    args = parser.parse_args()

    run(
        source=args.source,
        company_name=args.company,
        start_date=args.start_date,
        end_date=args.end_date,
        product_url=args.product_url,
        product_slug=args.product_slug,
        output=args.output,
        max_pages=args.max_pages,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
