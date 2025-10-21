# Scrapy settings for accela_work project

BOT_NAME = "accela_work"

SPIDER_MODULES = ["accela_work.spiders"]
NEWSPIDER_MODULE = "accela_work.spiders"


# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Set settings whose default value is deprecated to a future-proof value
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
