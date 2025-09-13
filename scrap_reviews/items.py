import scrapy


class ReviewItem(scrapy.Item):
    source = scrapy.Field()        # g2, capterra, etc.
    company_name = scrapy.Field()
    title = scrapy.Field()
    review_text = scrapy.Field()
    date = scrapy.Field()          # YYYY-MM-DD when possible
    rating = scrapy.Field()
    reviewer_name = scrapy.Field()
    scraped_at = scrapy.Field()
