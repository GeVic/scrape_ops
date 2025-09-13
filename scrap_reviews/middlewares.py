from __future__ import annotations

import random
import time
from typing import Iterable

from scrapy import signals
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware



class ScrapReviewsSpiderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        return None

    def process_spider_output(self, response, result, spider):
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        return None

    def process_start_requests(self, start_requests, spider):
        for r in start_requests:
            yield r

    async def process_start(self, start):
        async for r in start:
            yield r

    def spider_opened(self, spider):
        spider.logger.info(f"Spider opened: {spider.name}")


class ScrapReviewsDownloaderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        return None

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        return None

    def spider_opened(self, spider):
        spider.logger.info(f"Spider opened: {spider.name}")


class RandomUserAgentMiddleware(UserAgentMiddleware):
    def __init__(self, user_agent: str = "Scrapy", user_agent_list: Iterable[str] | None = None):
        super().__init__(user_agent)
        self.user_agent_list = list(user_agent_list or []) or [
            # Common desktop UAs
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        ]

    @classmethod
    def from_crawler(cls, crawler):
        ualist = crawler.settings.getlist("USER_AGENT_LIST")
        return cls(user_agent=crawler.settings.get("USER_AGENT", "Scrapy"), user_agent_list=ualist)

    def process_request(self, request, spider):
        request.headers["User-Agent"] = random.choice(self.user_agent_list)
        return None


class RandomDelayMiddleware:
    def __init__(self, delay: float = 1.0, randomize: float = 2.0):
        self.delay = delay
        self.randomize = randomize

    @classmethod
    def from_crawler(cls, crawler):
        base = float(crawler.settings.get("DOWNLOAD_DELAY", 1.0))
        rand = float(crawler.settings.get("RANDOMIZE_DOWNLOAD_DELAY", 2.0))
        return cls(delay=base, randomize=rand)

    def process_request(self, request, spider):
        # Simple blocking delay, acceptable for low concurrency
        sleep_for = self.delay + random.uniform(0, self.randomize)
        time.sleep(max(0.0, sleep_for))
        return None


class AntiBotDetectionMiddleware:
    def process_request(self, request, spider):
        request.headers.setdefault("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8")
        request.headers.setdefault("Accept-Language", "en-US,en;q=0.5")
        request.headers.setdefault("Accept-Encoding", "gzip, deflate, br")
        request.headers.setdefault("DNT", "1")
        request.headers.setdefault("Connection", "keep-alive")
        request.headers.setdefault("Upgrade-Insecure-Requests", "1")
        # Optional referer
        ref = getattr(spider, "referer", None)
        if ref:
            request.headers.setdefault("Referer", ref)
        return None
