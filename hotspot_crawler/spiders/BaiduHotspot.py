# -*- coding: utf-8 -*-
import re

from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from ..items import HotspotCrawlerItem, HotspotCrawlerItemLoader


class BaiduHotspotSpider(CrawlSpider):
    name = 'BaiduHotspot'
    allowed_domains = ['baidu.com', ]
    start_urls = ['http://news.baidu.com/', ]

    rules = (
        Rule(LinkExtractor(allow=r"https?://baijiahao.baidu.com/s\?id=\w+",
                           restrict_xpaths=['//div[@id="pane-news"]//a[@href]',
                                            '//div[@id="baijia"]//a[@href]'
                                            '//div[@class="civilnews"]//a[@href]',
                                            '//div[@class="InternationalNews"]//a[@href]',
                                            '//div[@class="EnterNews"]//a[@href]',
                                            '//div[@class="SportNews"]//a[@href]',
                                            '//div[@class="FinanceNews"]//a[@href]',
                                            ]), callback='parse_item_baidu',
             follow=True),
    )

    def parse_item_baidu(self, response):
        if re.match(r"https?://baijiahao\.baidu\.com/s\?id=\w+", string=response.url) is None:
            return None
        # url示例：http://baijiahao.baidu.com/s?id=1638368912732698067
        self.logger.info("parsing url %s" % response.url)
        item_loader = HotspotCrawlerItemLoader(item=HotspotCrawlerItem(), response=response)
        try:
            item_loader.add_value("newsId", response.url.split('/')[-1][5:])
            item_loader.add_css("title", 'head>title::text')
            item_loader.add_value("source", "百度")
            item_loader.add_css("source_from", 'div.author-txt > p::text')
            time_str = response.css(
                'div.author-txt > div>span.date::text, div.author-txt>div>span.time::text').extract()
            # 拿到的值类似于['07-03','10:08']
            import datetime
            today = datetime.datetime.now()
            time_str[0] = re.sub(r"发布时间[：:]", repl="", string=time_str[0])
            time_str[0] = str(today.year) + '-' + time_str[0]
            item_loader.add_value("publish_time", " ".join(time_str))
            item_loader.add_value("keywords", [])
            item_loader.add_value("content_url", response.url)
            media_url = {}
            media_url.update(
                {"img_url": response.css('.img-container>img::attr(src)').extract() or []}
            )
            media_url.update(
                {"video_url": response.css('.video-container>video::attr(src)').extract() or []}
            )
            item_loader.add_value("abstract", "")
            item_loader.add_value("media_url", media_url)
            # 要拿到所有p标签下的文字，用add_value
            content_list = response.css('div.article-content > p::text').extract()
            if content_list is []:
                content_list = response.css('div.article-content>p>span::text').extract()
            content = '\n'.join(content_list)
            content = self.replace_spaces_and_comments(content)
            item_loader.add_value("content", content)
            hot_data = self.get_hot_statistics()
            item_loader.add_value("hot_data", hot_data)
            return item_loader.load_item()
        except Exception as e:
            self.logger.critical(msg=e)
            return None

    def get_hot_statistics(self):
        return {
            "comment_num": "当前网站无法获得评论数信息",
            "participate_count": "当前网站无法获取参与人数信息"
        }

    def replace_spaces_and_comments(self, repl_text):
        import re
        repl_text = re.sub(r'\s+', repl="", string=repl_text)
        repl_text = re.sub(r'\u3000', repl="", string=repl_text)
        return re.sub(r'<!--\w+-->', repl="", string=repl_text)
