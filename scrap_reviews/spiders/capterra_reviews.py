import re
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

import scrapy

from scrap_reviews.items import ReviewItem
from scrap_reviews.utils import parse_date, in_date_range, slugify


class CapterraReviewsSpider(scrapy.Spider):
    name = "capterra_reviews"
    allowed_domains = ["capterra.com", "www.capterra.com", "proxy.scrapeops.io"]

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 1,
    }

    def __init__(
        self,
        company_name: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        product_url: str | None = None,
        product_slug: str | None = None,
        max_pages: int | None = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.company_name = company_name or ""
        self.start_date = start_date
        self.end_date = end_date
        self.max_pages = int(max_pages) if max_pages else None

        if product_url:
            variants = [product_url]
            if "/reviews" not in product_url:
                base = product_url.rstrip("/")
                variants += [f"{base}/reviews", f"{base}/reviews/"]
            self.candidate_urls = [self._ensure_render_js(u) for u in variants]
        else:
            raw = (product_slug or self.company_name or "").strip()
            path = None
            name_slug = None
            if "/" in raw and any(ch.isdigit() for ch in raw):
                path = raw.strip("/ ")
            elif raw.isdigit():
                path = raw
            else:
                name_slug = slugify(raw)
            base = []
            if name_slug:
                base += [
                    f"https://www.capterra.com/reviews/{name_slug}/",
                    f"https://www.capterra.com/reviews/{name_slug}",
                    f"https://www.capterra.com/{name_slug}/reviews/",
                    f"https://www.capterra.com/{name_slug}/",
                ]
            if path:
                base += [
                    f"https://www.capterra.com/p/{path}/reviews/",
                    f"https://www.capterra.com/p/{path}/",
                ]
            if not path and name_slug:
                base += [
                    f"https://www.capterra.com/p/{name_slug}/reviews/",
                    f"https://www.capterra.com/p/{name_slug}/",
                ]
            self.candidate_urls = [self._ensure_render_js(u) for u in base]

        self.page = 1

    def _ensure_render_js(self, url: str) -> str:
        p = urlparse(url)
        qs = parse_qs(p.query)
        qs.setdefault("render_js", ["true"])
        return urlunparse(p._replace(query=urlencode(qs, doseq=True)))

    def start_requests(self):
        urls = getattr(self, "candidate_urls", [])
        if not urls:
            return
        url = urls[0]
        if "page=" not in url:
            sep = "&" if urlparse(url).query else "?"
            url = f"{url}{sep}page=1"
        self.logger.info(f"Capterra: trying candidate URL 1/{len(urls)} -> {url}")
        yield scrapy.Request(url, callback=self.try_start, meta={"render_js": True, "wait": 4000, "cand_idx": 0, "handle_httpstatus_all": True})

    def try_start(self, response):
        # If this page contains review cards, proceed; else try next candidate
        if response.status >= 400:
            self.logger.info(f"Capterra: HTTP {response.status} on {response.url}; trying next candidate")
            idx = int(response.meta.get("cand_idx", 0))
            urls = getattr(self, "candidate_urls", [])
            if idx + 1 < len(urls):
                next_url = urls[idx + 1]
                if "page=" not in next_url:
                    sep = "&" if urlparse(next_url).query else "?"
                    next_url = f"{next_url}{sep}page=1"
                self.logger.info(f"Capterra: switching candidate -> {next_url}")
                yield scrapy.Request(
                    next_url,
                    callback=self.try_start,
                    meta={"render_js": True, "wait": 4000, "cand_idx": idx + 1, "handle_httpstatus_all": True},
                )
            else:
                self.logger.warning(f"No valid Capterra reviews URL found for company={self.company_name}. Tried: {urls}")
            return

        selectors = [
            '[itemprop="review"]',
            'article[data-test*="review"]',
            'div[data-test*="review"]',
            'section[data-test*="review"]',
            'article[class*="review"]',
            'div[class*="review-card"]',
            'div[class*="review"]',
            # Heuristic fallback based on provided HTML snippet
            'div.p-6.space-y-4',
            'div.p-6.space-y-8',
            'div[class*="p-6"][class*="space-y-"]',
        ]
        for s in selectors:
            if response.css(s):
                self.logger.info(f"Capterra: found reviews on {response.url}, proceeding (css: {s})")
                yield from self.parse(response)
                return

        # XPath fallbacks (avoid unsupported :has() in cssselect)
        xpaths = [
            "//*[@itemprop='review']",
            "//article[contains(@class,'review') or contains(@data-test,'review')]",
            "//div[contains(@class,'review-card') or contains(@class,'review') or contains(@data-test,'review')]",
            "//section[contains(@class,'review') or contains(@data-test,'review')]",
            # Heuristic fallback container: p-6 + space-y-* and mention of 'Used the software for'
            "//div[contains(@class,'p-6') and contains(@class,'space-y-')]",
            "//div[contains(@class,'p-6') and contains(@class,'space-y-')][.//text()[contains(., 'Used the software for')]]",
        ]
        for xp in xpaths:
            if response.xpath(xp):
                self.logger.info(f"Capterra: found reviews on {response.url}, proceeding (xpath)")
                yield from self.parse(response)
                return

        idx = int(response.meta.get("cand_idx", 0))
        urls = getattr(self, "candidate_urls", [])
        if idx + 1 < len(urls):
            next_url = urls[idx + 1]
            if "page=" not in next_url:
                sep = "&" if urlparse(next_url).query else "?"
                next_url = f"{next_url}{sep}page=1"
            self.logger.info(f"Capterra: no reviews detected on {response.url}, trying next candidate -> {next_url}")
            yield scrapy.Request(
                next_url,
                callback=self.try_start,
                meta={"render_js": True, "wait": 4000, "cand_idx": idx + 1, "handle_httpstatus_all": True},
            )
        else:
            self.logger.warning(f"No valid Capterra reviews URL found for company={self.company_name}. Tried: {urls}")

    def _text(self, sel, css_query: str) -> str | None:
        v = sel.css(css_query).get()
        if not v:
            return None
        v = re.sub(r"\s+", " ", scrapy.selector.unified.Selector(text=v).xpath("string()").get() or "").strip()
        return v or None

    def _extract_rating(self, card) -> str | None:
        v = card.css('meta[itemprop="ratingValue"]::attr(content)').get()
        if v:
            return v.strip()
        v = self._text(card, '[itemprop="reviewRating"]::attr(content)')
        if v:
            return v
        v = self._text(
            card,
            '[aria-label*="out of 5"]::attr(aria-label), [class*="rating"]::text, .stars::text, [data-star-rating]::attr(data-star-rating)',
        )
        if v:
            m = re.search(r"(\d+(?:\.\d+)?)", v)
            if m:
                return m.group(1)
        stars = card.css('[class*="star"][class*="filled"], [class*="star"][aria-hidden="false"]').getall()
        if stars:
            return str(len(stars))
        return None

    def _extract_date(self, card) -> str | None:
        for q in [
            'meta[itemprop="datePublished"]::attr(content)',
            "time::attr(datetime)",
            ".review-date::text",
            "[data-test*='date']::text",
            "span.ms-2::text",
            "time::text",
        ]:
            raw = card.css(q).get()
            if raw:
                iso = parse_date(raw)
                if iso:
                    return iso
        return None

    def parse(self, response):
        cards = []
        for q in [
            # common Capterra structures and fallbacks
            '[itemprop="review"]',
            'article[data-test*="review"]',
            'div[data-test*="review"]',
            'section[data-test*="review"]',
            'article[class*="review"]',
            'div[class*="review-card"]',
            'div[class*="review"]',
            # Heuristic fallback based on provided HTML snippet
            'div.p-6.space-y-4',
            'div.p-6.space-y-8',
            'div[class*="p-6"][class*="space-y-"]',
        ]:
            found = response.css(q)
            if found:
                cards = found
                break

        # JSON-LD fallback when DOM selectors don't find cards
        if not cards:
            for script_text in response.css('script[type="application/ld+json"]::text').getall():
                try:
                    import json
                    data = json.loads(script_text)
                except Exception:
                    continue

                objs = data if isinstance(data, list) else [data]
                for obj in objs:
                    if not isinstance(obj, dict):
                        continue

                    reviews = []
                    if obj.get("@type") == "Review":
                        reviews = [obj]
                    elif obj.get("@type") in ("Product", "SoftwareApplication"):
                        r = obj.get("review") or obj.get("reviews")
                        if isinstance(r, list):
                            reviews = r
                        elif isinstance(r, dict):
                            reviews = [r]

                    for r in reviews:
                        if not isinstance(r, dict):
                            continue
                        date_iso = parse_date(r.get("datePublished") or r.get("dateCreated") or r.get("date"))
                        if not in_date_range(date_iso, self.start_date, self.end_date):
                            continue

                        item = ReviewItem()
                        item["source"] = "capterra"
                        item["company_name"] = self.company_name
                        item["title"] = r.get("headline") or r.get("name")
                        item["review_text"] = r.get("reviewBody") or r.get("description")

                        rating_val = None
                        rating_obj = r.get("reviewRating") or r.get("aggregateRating")
                        if isinstance(rating_obj, dict):
                            rating_val = rating_obj.get("ratingValue")
                        item["rating"] = rating_val

                        author = r.get("author")
                        if isinstance(author, dict):
                            item["reviewer_name"] = author.get("name")
                        elif isinstance(author, str):
                            item["reviewer_name"] = author

                        item["date"] = date_iso

                        if item.get("review_text") and item.get("date"):
                            yield item
            return

        for card in cards:
            date_iso = self._extract_date(card)
            if not in_date_range(date_iso, self.start_date, self.end_date):
                continue

            item = ReviewItem()
            item["source"] = "capterra"
            item["company_name"] = self.company_name

            title = (
                self._text(card, '[data-test="review-title"]::text')
                or self._text(card, "h3::text")
                or self._text(card, "h2::text")
                or self._text(card, "header h3::text")
            )
            body = (
                self._text(card, '[itemprop="reviewBody"]')
                or self._text(card, ".review-text")
                or self._text(card, ".review-content")
                or self._text(card, "[data-test='review-body']")
                or self._text(card, "p")
            )
            if not title and body:
                t = body.strip()
                title = (t[:80] + "...") if len(t) > 80 else t
            reviewer = (
                card.css('[itemprop="author"] [itemprop="name"]::attr(content)').get()
                or self._text(card, '[itemprop="author"]::text')
                or self._text(card, ".reviewer-name::text, .author-name::text, [data-test='reviewer-name']::text")
            )

            item["title"] = title
            item["review_text"] = body
            item["date"] = date_iso
            item["rating"] = self._extract_rating(card)
            item["reviewer_name"] = reviewer

            if not item.get("review_text") or not item.get("date"):
                continue

            yield item

        if self.max_pages and self.page >= self.max_pages:
            return

        next_href = response.css(
            'a[rel="next"]::attr(href), a[aria-label="Next"]::attr(href), .pagination .next a::attr(href), .pagination-next::attr(href)'
        ).get()
        next_url = urljoin(response.url, next_href) if next_href else None

        if not next_url:
            p = urlparse(response.url)
            qs = parse_qs(p.query)
            cur = int(qs.get("page", ["1"])[0])
            qs["page"] = [str(cur + 1)]
            next_url = urlunparse(p._replace(query=urlencode(qs, doseq=True)))

        self.page += 1
        if next_url:
            next_url = self._ensure_render_js(next_url)
            yield scrapy.Request(next_url, callback=self.parse, meta={"render_js": True, "wait": 4000})
