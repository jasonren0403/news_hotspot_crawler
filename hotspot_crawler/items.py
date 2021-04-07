# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import itemloaders
from itemloaders import ItemLoader
from scrapy.item import Item, Field
from w3lib.html import remove_tags, remove_comments


class HotspotCrawlerItemLoader(ItemLoader):
    default_output_processor = itemloaders.processors.TakeFirst()

    @classmethod
    def remove_spaces_and_comments(cls, repl_text):
        import re
        content = remove_tags(repl_text)
        content = remove_comments(content)
        # 移除空格 换行
        return re.sub(r'[\t\r\n\s]', '', content)


class HotspotCrawlerItem(Item):
    # 新闻标题
    title = Field(
        input_processor=itemloaders.processors.MapCompose(HotspotCrawlerItemLoader.remove_spaces_and_comments))
    # 新闻来源
    source = Field()
    # 新闻二级来源（原发布网站）
    source_from = Field(
        input_processor=itemloaders.processors.MapCompose(HotspotCrawlerItemLoader.remove_spaces_and_comments))
    # 发布日期
    publish_time = Field()
    # 新闻Id，唯一标识
    newsId = Field()
    # 关键词
    keywords = Field(output_processor=itemloaders.processors.Identity(), )
    # 新闻内容详情网址
    content_url = Field()
    # 媒体网址
    media_url = Field()
    # 新闻内容详情
    content = Field(serializer=str, input_processor=itemloaders.processors.MapCompose(
        HotspotCrawlerItemLoader.remove_spaces_and_comments))
    # 热点数据（包括阅读数、参与or评论数）
    hot_data = Field()
    # 新闻摘要
    abstract = Field(serializer=str, input_processor=itemloaders.processors.MapCompose(
        HotspotCrawlerItemLoader.remove_spaces_and_comments))
