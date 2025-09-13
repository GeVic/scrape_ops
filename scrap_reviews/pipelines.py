from __future__ import annotations

import csv
import os
import re
from datetime import datetime

from itemadapter import ItemAdapter
from scrapy.exporters import JsonItemExporter
from scrapy.exceptions import DropItem
from scrap_reviews.utils import parse_date


class ScrapReviewsPipeline:
    def process_item(self, item, spider):
        return item


class DataValidationPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        text_fields = [
            "source",
            "company_name",
            "product_name",
            "product_url",
            "category",
            "product_description",
            "pricing",
            "reviewer_name",
            "reviewer_role",
            "reviewer_company",
            "reviewer_company_size",
            "reviewer_industry",
            "review_title",
            "review_text",
            "pros",
            "cons",
            "recommendations",
            "date",
            "review_date",
        ]
        for f in text_fields:
            if f in adapter:
                val = adapter.get(f)
                if val is None:
                    continue
                cleaned = " ".join(str(val).split())
                adapter[f] = cleaned if cleaned else None

        numeric_fields = ["rating", "total_reviews", "total_products", "review_count"]
        for f in numeric_fields:
            if f in adapter:
                val = adapter.get(f)
                if val is None:
                    adapter[f] = None
                    continue
                try:
                    if isinstance(val, (int, float)):
                        adapter[f] = float(val)
                    else:
                        nums = re.findall(r"\d+\.?\d*", str(val).replace(",", ""))
                        adapter[f] = float(nums[0]) if nums else None
                except (ValueError, TypeError):
                    adapter[f] = None

        # Normalize to minimal ReviewItem schema across sources
        if "review_text" in adapter:
            # company_name fallback
            if not adapter.get("company_name") and adapter.get("product_name"):
                adapter["company_name"] = adapter.get("product_name")

            # title
            if not adapter.get("title"):
                title = adapter.get("review_title")
                if not title:
                    text = adapter.get("review_text") or ""
                    title = (text[:80] + "...") if len(text) > 80 else text
                adapter["title"] = title

            # date normalization
            raw_date = adapter.get("date") or adapter.get("review_date")
            if raw_date:
                iso = parse_date(raw_date)
                if iso:
                    adapter["date"] = iso

            # infer source from spider name or URL
            if not adapter.get("source"):
                name = (getattr(spider, "name", "") or "").lower()
                src = None
                if "g2" in name:
                    src = "g2"
                elif "capterra" in name:
                    src = "capterra"
                elif "trustpilot" in name:
                    src = "trustpilot"
                else:
                    pu = adapter.get("product_url") or ""
                    if "g2.com" in pu:
                        src = "g2"
                    elif "capterra.com" in pu:
                        src = "capterra"
                    elif "trustpilot.com" in pu:
                        src = "trustpilot"
                if src:
                    adapter["source"] = src

            # enforce required fields
            if not adapter.get("review_text"):
                raise DropItem("Review missing review_text")
            if not adapter.get("date"):
                raise DropItem("Review missing date")
            if not adapter.get("title"):
                text = adapter.get("review_text") or ""
                adapter["title"] = (text[:80] + "...") if len(text) > 80 else text

        adapter["scraped_at"] = datetime.now().isoformat()
        return item


class DuplicatesPipeline:
    def __init__(self):
        self.ids_seen = set()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        item_id = None
        # Normalized review item
        if "review_text" in adapter and ("date" in adapter or "review_date" in adapter):
            d = adapter.get("date") or adapter.get("review_date") or ""
            reviewer = adapter.get("reviewer_name") or ""
            src = adapter.get("source") or ""
            snippet = (adapter.get("review_text") or "")[:50]
            item_id = f"review_{src}_{reviewer}_{d}_{snippet}"
        # G2 product vs review items
        elif "product_name" in adapter and "product_url" in adapter and "reviewer_name" not in adapter:
            item_id = f"product_{adapter.get('product_name')}_{adapter.get('product_url')}"
        elif "category_name" in adapter:
            item_id = f"category_{adapter.get('category_name')}"

        if not item_id:
            return item

        if item_id in self.ids_seen:
            raise DropItem(f"Duplicate item: {item_id}")
        self.ids_seen.add(item_id)
        return item


class JsonExportPipeline:
    def __init__(self):
        self.files = {}
        self.exporters = {}
        self.active_types = set()

    def open_spider(self, spider):
        os.makedirs("data", exist_ok=True)

    def close_spider(self, spider):
        for exporter in self.exporters.values():
            exporter.finish_exporting()
        for f in self.files.values():
            f.close()

    def _item_type(self, adapter: ItemAdapter) -> str | None:
        if "product_name" in adapter:
            return "review" if "reviewer_name" in adapter else "product"
        if "category_name" in adapter:
            return "category"
        if "review_text" in adapter:
            return "review"
        return None

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        t = self._item_type(adapter)
        if not t:
            return item

        if t not in self.active_types:
            filename = f"data/{t}s_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            f = open(filename, "wb")
            exp = JsonItemExporter(f, encoding="utf-8", ensure_ascii=False, indent=2)
            exp.start_exporting()
            self.files[t] = f
            self.exporters[t] = exp
            self.active_types.add(t)

        self.exporters[t].export_item(item)
        return item


class CsvExportPipeline:
    def __init__(self):
        self.files = {}
        self.csv_writers = {}
        self.headers_written = set()
        self.spider_start_time = None
        self.active_types = set()

    def open_spider(self, spider):
        os.makedirs("data", exist_ok=True)
        self.spider_start_time = datetime.now().strftime("%Y%m%d_%H%M%S")

    def close_spider(self, spider):
        for f in self.files.values():
            f.close()

    def _item_type(self, adapter: ItemAdapter) -> str | None:
        if "product_name" in adapter:
            return "review" if "reviewer_name" in adapter else "product"
        if "category_name" in adapter:
            return "category"
        if "review_text" in adapter:
            return "review"
        return None

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        t = self._item_type(adapter)
        if not t:
            return item

        row = {}
        for k in adapter.field_names():
            v = adapter.get(k)
            if isinstance(v, bytes):
                row[k] = v.decode("utf-8", errors="ignore")
            elif v is None:
                row[k] = ""
            else:
                row[k] = str(v)

        if t not in self.active_types:
            filename = f"data/{t}s_{self.spider_start_time}.csv"
            f = open(filename, "w", newline="", encoding="utf-8")
            w = csv.writer(f)
            self.files[t] = f
            self.csv_writers[t] = w
            self.active_types.add(t)
            w.writerow(row.keys())

        self.csv_writers[t].writerow(row.values())
        return item


class LoggingPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        if "product_name" in adapter and "reviewer_name" not in adapter:
            spider.logger.info(f"Product: {adapter.get('product_name')}")
        elif "category_name" in adapter:
            spider.logger.info(f"Category: {adapter.get('category_name')}")
        elif "reviewer_name" in adapter or "review_text" in adapter:
            spider.logger.info("Review item")
        return item
