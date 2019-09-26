# -*- coding: utf-8 -*-
import copy
import time
import urllib

import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from ..items import HotspotCrawlerItem, HotspotCrawlerItemLoader


class XinhuaHotspotSpider(CrawlSpider):
    name = 'XinhuaHotspot'
    allowed_domains = ['xinhuanet.com']
    start_urls = ['http://www.xinhuanet.com/', "https://www.xinhuanet.com/", ]

    now_yearmonth = time.strftime("%Y-%m", time.localtime())
    now_day = time.strftime("%d", time.localtime())
    reg = r"https?://www\.xinhuanet\.com/\w+/ym/day/c_\d+"
    reg = reg.replace("ym", now_yearmonth).replace("day", now_day)
    rules = (
        Rule(LinkExtractor(allow=reg, deny=(
            r"https?://www\.xinhuanet\.com/english/\S+",
            r"https?://www\.xinhuanet\.com/photo/\S+",
            r"https?://www\.xinhuanet\.com/video/\S+")),
             follow=True, callback='parse_items_xinhua'),
    )

    def parse_items_xinhua(self, response):
        # url示例：http://www.xinhuanet.com/fortune/2019-07/07/c_1210182505.htm
        print("parsing url %s" % response.url)
        global request_more
        if response.meta.get('item') is None:
            item_loader = HotspotCrawlerItemLoader(item=HotspotCrawlerItem(), response=response)
            request_more = True
        else:
            item_loader = response.meta['item']
            print(item_loader.get_collected_values)
            request_more = False
        try:
            import re
            if not item_loader.get_collected_values("title"):
                item_loader.add_css("title", ".share-title::text")
            if not item_loader.get_collected_values("source_from"):
                if response.css('#source'):
                    item_loader.add_css("source_from", '#source::text')
                else:
                    source_from = response.css('.h-info > span:nth-child(2)::text').extract_first()
                    # 处理\r\n和空格
                    source_from = re.sub(r"\s+", "", source_from)
                    # 来源：xxx
                    item_loader.add_value("source_from", source_from.replace("来源：", ""))
            item_loader.add_value("source", "新华网")
            newsId = response.url.split('/')[-1].strip('.html')
            # 处理c_1124726204_2类的分页新闻
            newsId = re.findall(r"c_\d{9,}", newsId)[0]
            if not item_loader.get_collected_values("newsId") or item_loader.get_collected_values("newsId") != newsId:
                item_loader.add_value("newsId", newsId)
            # keywords 示例：'中国经济,世界经济,依存度\r\n' -> ['中国经济','世界经济','依存度']
            keywords = list(
                set(response.css('meta[name="keywords"]::attr(content)').extract_first().strip().split(','))) or []
            item_loader.add_value("keywords", keywords)
            item_loader.add_css("publish_time", '.h-time::text')
            item_loader.add_value("content_url", response.url)
            item_loader.add_css("abstract", 'meta[name="description"]::attr(content)')
            content = response.css('#p-detail>p').extract() or response.css(
                '#content>p::text, #content>p>span::text').extract()
            item_loader.add_value("content", self.deal_with_content(''.join(content)))
            media_url = {}
            img_urls = response.xpath('//*[@id="p-detail"]//img//@src').extract() or response.css(
                '#content>p>img::attr(src)').extract()
            media_url.update({
                "img_url": [urllib.parse.urljoin(response.url, i) for i in img_urls if not i.startswith('http')],
            })
            media_url.update({
                "video_url": response.css('.pageVideo::attr(src)').extract() or [],
            })
            item_loader.add_value("media_url", media_url)
            hot_data = self.get_hot_statistics(response, newsId)
            item_loader.add_value("hot_data", hot_data)
            more_pages = response.css('#div_currpage>a::attr(href)').extract()
            if more_pages and not request_more:
                # 先去重
                temp = list(set(more_pages))
                temp.sort(key=more_pages.index)
                for url in temp:
                    print("more pages,continue parsing")
                    yield scrapy.Request(
                        url=url, callback=self.parse_items_xinhua,
                        meta=copy.deepcopy({'item': item_loader.load_item()})
                    )
            yield item_loader.load_item()
        except Exception as e:
            self.logger.critical(msg=e)
            return None

    def get_hot_statistics(self, response, newsId):
        import requests, string, random, re, json
        url = 'http://comment.home.news.cn/a/newsInfo.do?newsId={}&callback=jQuery{}_{}&_={}'
        newsId = newsId.strip('c_')
        newsId = "1-" + newsId
        ran_num = ''.join(random.sample(3 * string.digits, 21))
        microsecond = int(time.time() * 1000)
        req = requests.get(url=url.format(newsId, ran_num, microsecond, microsecond + 1), headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36",
        })
        # print(req.url)
        content = req.text.strip(';')
        content = re.sub(r"jQuery\d+_\d+", repl="", string=content)
        content = content.strip('()')
        try:
            datas = json.loads(content)
        except:
            datas = json.loads(content.replace(');', ''))
        if not datas.get('code'):
            comment_num = datas.get("commAmount")
            participate_count = datas.get("downAmount") + datas.get("upAmount")
            return {
                "comment_num": comment_num,
                "participate_count": participate_count
            }
        else:
            return {
                "comment_num": datas.get('code') + datas.get('description'),
                "participate_count": datas.get('code') + datas.get('description')
            }

    def deal_with_content(self, repl_text):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(repl_text, "lxml")
        contents = soup.find_all('p')
        return ''.join(i.string for i in contents if i.string) or ""
