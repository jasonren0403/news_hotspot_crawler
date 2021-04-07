# -*- coding: utf-8 -*-
import re

from scrapy.linkextractors import LinkExtractor
from scrapy.selector import Selector
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
        selector = Selector(response=response, type='html')
        item_loader = HotspotCrawlerItemLoader(item=HotspotCrawlerItem(), selector=selector)
        try:
            item_loader.add_value("newsId", response.url.split('/')[-1][5:])
            item_loader.add_css("title", 'head>title::text')
            item_loader.add_value("source", "百度")
            item_loader.add_css("source_from", 'p.index-module_authorName_7y5nA::text')
            time_str = response.css(
                'div.index-module_articleSource_2dw16>span::text').extract()
            # 拿到的值类似于['07-03','10:08']
            # self.logger.info(msg=time_str)
            import datetime
            today = datetime.datetime.now()
            time_str[0] = re.sub(r"发布时间[：:]", repl="", string=time_str[0]).strip()
            time_str[0] = str(today.year) + '-' + time_str[0]
            if response.css('span.index-module_accountAuthentication_3BwIx') is not None and time_str:
                time_str.remove(time_str[-1])
            item_loader.add_value("publish_time", " ".join(time_str))
            item_loader.add_value("keywords", [])
            item_loader.add_value("content_url", response.url)
            media_url = {}
            media_url.update(
                {"img_url": response.css(
                    '.index-module_mediaWrap_213jB>.index-module_contentImg_JmmC0>img::attr(src)').extract() or []}
            )
            media_url.update(
                {"video_url": response.css('.video-container>video::attr(src)').extract() or []}
            )
            item_loader.add_value("abstract", "")
            item_loader.add_value("media_url", media_url)
            # 要拿到所有p标签下的文字，用add_value
            content_list = response.css('div.index-module_textWrap_3ygOc > p::text').extract()
            content = '\n'.join(content_list)
            content = self.replace_spaces_and_comments(content)
            item_loader.add_value("content", content)
            hot_data = self.get_hot_statistics(response, response.url.split('/')[-1][5:])
            item_loader.add_value("hot_data", hot_data)
            return item_loader.load_item()
        except Exception as e:
            self.logger.exception(msg=e)
            return None

    def get_hot_statistics(self, response, newsID: str) -> dict:
        # window.jsonData = ....
        self.logger.info(f"[NewsID->{newsID}] Getting comment data...")
        # https://ext.baidu.com/api/comment/v2/comment/list?
        # thread_id=1002000040186955
        # &reply_id=
        # &start=0
        # &num=20
        # &appid=22862035
        # &ts={ts}
        selector = Selector(response=response, type='html')
        lst = selector.css('body>script::text').extract_first()
        if 'window.jsonData' in lst:
            participate = 0
            cmt_num = 0
            first_request = True
            lst = lst.lstrip('/* 后端数据jsonData */window.jsonData = ')
            lst = lst.rstrip(';window.firstScreenTime = Date.now();')
            import json
            win_data = json.loads(lst)
            cmnt_info = win_data['bsData']['comment']
            tid = cmnt_info['tid']
            can_comment = not cmnt_info['forbidden']
            if can_comment:
                import requests, time
                current_cmt = 0
                while current_cmt < cmt_num or first_request:
                    self.logger.info(
                        f'{"Total number " + str(cmt_num) if not first_request else ""} Requesting api starting from {current_cmt}')
                    dt = requests.get('https://ext.baidu.com/api/comment/v2/comment/list', params={
                        'thread_id': tid,
                        'reply_id': '',
                        'start': str(current_cmt),
                        'num': "20",
                        'appid': '22862035',
                        'ts': int(round(time.time() * 1000))
                    })
                    req = dt.json()
                    if req and req['errno'] == 0:
                        cmt_num = int(req['ret']['comment_count'])
                        cmt_list = req['ret']['list']
                        for person in cmt_list:
                            likes = person['like_count']
                            dislikes = person['dislike_count']
                            participate += 2 * likes + dislikes
                        current_cmt += len(cmt_list)
                    first_request = False
            return {
                'comment_num': cmt_num,
                'participate_count': participate
            }
        return {
            "comment_num": "当前网站无法获得评论数信息",
            "participate_count": "当前网站无法获取参与人数信息"
        }

    def replace_spaces_and_comments(self, repl_text):
        import re
        repl_text = re.sub(r'\s+', repl="", string=repl_text)
        repl_text = re.sub(r'\u3000', repl="", string=repl_text)
        return re.sub(r'<!--\w+-->', repl="", string=repl_text)
