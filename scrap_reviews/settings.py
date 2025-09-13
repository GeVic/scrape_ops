# Scrapy settings for scrap_reviews project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "scrap_reviews"

SPIDER_MODULES = ["scrap_reviews.spiders"]
NEWSPIDER_MODULE = "scrap_reviews.spiders"

ADDONS = {}


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "scrap_reviews (+http://www.yourdomain.com)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Concurrency and throttling settings
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 1

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
SPIDER_MIDDLEWARES = {
    "scrap_reviews.middlewares.ScrapReviewsSpiderMiddleware": 543,
}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    "scrap_reviews.middlewares.ScrapReviewsDownloaderMiddleware": 543,
    "scrap_reviews.middlewares.RandomUserAgentMiddleware": 400,
    "scrap_reviews.middlewares.RandomDelayMiddleware": 401,
    "scrap_reviews.middlewares.AntiBotDetectionMiddleware": 402,
    "scrapeops_scrapy_proxy_sdk.scrapeops_scrapy_proxy_sdk.ScrapeOpsScrapyProxySdk": 725,
}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    "scrap_reviews.pipelines.DataValidationPipeline": 300,
    "scrap_reviews.pipelines.DuplicatesPipeline": 400,
    "scrap_reviews.pipelines.LoggingPipeline": 500,
    "scrap_reviews.pipelines.JsonExportPipeline": 600,
    "scrap_reviews.pipelines.CsvExportPipeline": 700,
}


AUTOTHROTTLE_ENABLED = True

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403]

# User agent rotation
USER_AGENT_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

# ScrapeOps proxy (optional) - env-driven
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY")
SCRAPEOPS_PROXY_ENABLED = os.getenv("SCRAPEOPS_PROXY_ENABLED", "false").lower() in ("1", "true", "yes", "on")
SCRAPEOPS_RENDER_JS = os.getenv("SCRAPEOPS_RENDER_JS", "true").lower() in ("1", "true", "yes", "on")
SCRAPEOPS_WAIT_MS = int(os.getenv("SCRAPEOPS_WAIT_MS", "2000"))
SCRAPEOPS_KEEP_HEADERS = os.getenv("SCRAPEOPS_KEEP_HEADERS", "true").lower() in ("1", "true", "yes", "on")
