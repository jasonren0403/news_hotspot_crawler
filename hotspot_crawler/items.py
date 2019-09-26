# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field
from scrapy.loader import ItemLoader
from scrapy.loader.processors import MapCompose, TakeFirst, Identity


class HotspotCrawlerItemLoader(ItemLoader):
    default_output_processor = TakeFirst()

    @classmethod
    def remove_spaces_and_comments(cls, repl_text):
        import re
        repl_text = re.sub(r'\s+', repl="", string=repl_text)
        repl_text = re.sub(r'\u3000', repl="", string=repl_text)
        return re.sub(r'<!--\S+-->', repl="", string=repl_text)


class HotspotCrawlerItem(Item):
    # 新闻标题
    title = Field(input_processor=MapCompose(HotspotCrawlerItemLoader.remove_spaces_and_comments))
    # 新闻来源
    source = Field()
    # 新闻二级来源（原发布网站）
    source_from = Field(input_processor=MapCompose(HotspotCrawlerItemLoader.remove_spaces_and_comments))
    # 发布日期
    publish_time = Field()
    # 新闻Id，唯一标识
    newsId = Field()
    # 关键词
    keywords = Field(output_processor=Identity(), )
    # 新闻内容详情网址
    content_url = Field()
    # 媒体网址
    media_url = Field()
    # 新闻内容详情
    content = Field(serializer=str, input_processor=MapCompose(HotspotCrawlerItemLoader.remove_spaces_and_comments))
    # 热点数据（包括阅读数、参与or评论数）
    hot_data = Field()
    # 新闻摘要
    abstract = Field(serializer=str, input_processor=MapCompose(HotspotCrawlerItemLoader.remove_spaces_and_comments))
