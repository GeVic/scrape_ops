import re
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

import scrapy

from scrap_reviews.items import ReviewItem
from scrap_reviews.utils import parse_date, in_date_range, slugify


class G2ReviewsSpider(scrapy.Spider):
    name = "g2_reviews"
    allowed_domains = ["g2.com", "www.g2.com", "proxy.scrapeops.io"]

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
            self.candidate_urls = [self._ensure_render_js(product_url)]
        else:
            slug = product_slug or slugify(self.company_name)
            base = [
                f"https://www.g2.com/products/{slug}/reviews",
                f"https://www.g2.com/products/{slug}/reviews/",
                f"https://g2.com/products/{slug}/reviews",
                f"https://g2.com/products/{slug}/reviews/",
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
        self.logger.info(f"G2: trying candidate URL 1/{len(urls)} -> {url}")
        yield scrapy.Request(url, callback=self.try_start, meta={"render_js": True, "wait": 4000, "cand_idx": 0})

    def try_start(self, response):
        selectors = [
            'article.elv-bg-neutral-0',
            'article[data-testid*="review"]',
            'article[class*="review"]',
            'section[data-testid*="review"]',
            'section[class*="review"]',
            'div[data-testid*="review"]',
            'div[class*="review-card"]',
            '[itemprop="review"]',
            'article:has([itemprop="reviewRating"])',
            'section:has([itemprop="reviewRating"])',
            'div:has([itemprop="reviewRating"])',
        ]
        for s in selectors:
            if response.css(s):
                self.logger.info(f"G2: found reviews on {response.url}, proceeding")
                yield from self.parse(response)

        idx = int(response.meta.get("cand_idx", 0))
        urls = getattr(self, "candidate_urls", [])
        if idx + 1 < len(urls):
            next_url = urls[idx + 1]
            if "page=" not in next_url:
                sep = "&" if urlparse(next_url).query else "?"
                next_url = f"{next_url}{sep}page=1"
            self.logger.info(f"G2: no reviews detected on {response.url}, trying next candidate -> {next_url}")
            yield scrapy.Request(
                next_url,
                callback=self.try_start,
                meta={"render_js": True, "wait": 4000, "cand_idx": idx + 1},
            )
        else:
            self.logger.warning(f"No valid G2 reviews URL found for company={self.company_name}. Tried: {urls}")

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
        v = self._text(card, '[aria-label*="out of 5"]::attr(aria-label), [class*="rating"]::text, .stars::text')
        if v:
            m = re.search(r"(\d+(?:\.\d+)?)", v)
            if m:
                return m.group(1)
        return None

    def _extract_date(self, card) -> str | None:
        for q in [
            'meta[itemprop="datePublished"]::attr(content)',
            "time::attr(datetime)",
            ".review-date::text",
            ".date::text",
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
            'article.elv-bg-neutral-0',
            'article[data-testid*="review"]',
            'article[class*="review"]',
            'section[data-testid*="review"]',
            'section[class*="review"]',
            'div[data-testid*="review"]',
            'div[class*="review-card"]',
            '[itemprop="review"]',
            'article:has([itemprop="reviewRating"])',
            'section:has([itemprop="reviewRating"])',
            'div:has([itemprop="reviewRating"])',
        ]:
            found = response.css(q)
            if found:
                cards = found
                break

        self.logger.info(f"G2: detected {len(cards)} review containers on {response.url}")
        kept_in_range = 0
        if not cards:
            self.logger.warning(f"No review cards found for {response.url}")
        for card in cards:
            date_iso = self._extract_date(card)
            if not in_date_range(date_iso, self.start_date, self.end_date):
                continue

            item = ReviewItem()
            item["source"] = "g2"
            item["company_name"] = self.company_name

            title = (
                self._text(card, '[data-testid="review-title"]::text')
                or self._text(card, "h3::text")
                or self._text(card, "h2::text")
            )
            body = (
                self._text(card, '[itemprop="reviewBody"]')
                or self._text(card, ".review-text")
                or self._text(card, ".review-content")
                or self._text(card, "p")
            )
            reviewer = (
                card.css('[itemprop="author"] [itemprop="name"]::attr(content)').get()
                or self._text(card, '[itemprop="author"]::text')
                or self._text(card, ".reviewer-name::text, .author-name::text, .user-name::text")
            )

            if not title and body:
                t = body.strip()
                title = (t[:80] + "...") if len(t) > 80 else t

            item["title"] = title
            item["review_text"] = body
            item["date"] = date_iso
            item["rating"] = self._extract_rating(card)
            item["reviewer_name"] = reviewer

            # basic validation
            if not item.get("review_text") or not item.get("date"):
                continue
            kept_in_range += 1
            yield item

        self.logger.info(f"G2: kept {kept_in_range} of {len(cards)} within {self.start_date}..{self.end_date} on {response.url}")
        # pagination
        if self.max_pages and self.page >= self.max_pages:
            return

        next_href = (
            response.css('a[rel="next"]::attr(href), .pagination .next a::attr(href), .pagination-next::attr(href)').get()
        )
        next_url = urljoin(response.url, next_href) if next_href else None

        if not next_url:
            # fallback by incrementing page param
            p = urlparse(response.url)
            qs = parse_qs(p.query)
            cur = int(qs.get("page", ["1"])[0])
            qs["page"] = [str(cur + 1)]
            next_url = urlunparse(p._replace(query=urlencode(qs, doseq=True)))

        self.page += 1
        if next_url:
            next_url = self._ensure_render_js(next_url)
            yield scrapy.Request(next_url, callback=self.parse, meta={"render_js": True, "wait": 4000})
