# -*- coding: utf-8 -*-
import datetime
import time

from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from ..items import HotspotCrawlerItem, HotspotCrawlerItemLoader


class SinaHotspotSpider(CrawlSpider):
    name = 'SinaHotspot'
    allowed_domains = ['sina.com.cn', 'sina.com']
    start_urls = ['https://news.sina.com.cn/', ]
    reg = r"http(s)?://(\w+\.)?news.sina.com.cn/\w+/time/\w+-\w+\.(s)?html"
    t = time.localtime()
    now_time = time.strftime("%Y-%m-%d", t)
    reg = reg.replace("time", now_time)
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    yesterday_time = yesterday.strftime("%Y-%m-%d")
    reg2 = reg.replace("time", yesterday_time)
    rules = (
        Rule(LinkExtractor(
            allow=reg),
            callback='parse_sina_news', follow=True),
        Rule(LinkExtractor(
            allow=reg2),
            callback='parse_sina_news', follow=True),
    )

    def parse_sina_news(self, response):
        self.logger.info("parsing url %s" % response.url)
        # URL示例：https://news.sina.com.cn/s/2019-07-05/doc-ihytcerm1571229.shtml
        # start parsing #
        item_loader = HotspotCrawlerItemLoader(item=HotspotCrawlerItem(), response=response)
        try:
            item_loader.add_css("title", '.main-title::text') or ""
            item_loader.add_css("source_from",
                                'meta[property="article:author"]::attr(content)' or 'meta[name="mediaid"]::attr(content)')
            item_loader.add_value("source", "新浪新闻中心") or ""
            item_loader.add_css("publish_time", '.date-source>span::text') or ""
            item_loader.add_css("newsId", 'meta[name="publishid"]::attr(content)') or ""
            keywords = response.css('meta[name="keywords"]::attr(content)').extract_first().split(',')
            item_loader.add_value("keywords", list(set(keywords)))
            item_loader.add_css("content_url", 'meta[property="og:url"]::attr(content)') or response.url
            media_url = {}
            media_url.update(
                {"img_url": ["https:" + i for i in response.css('.img_wrapper>img::attr(src)').extract() if
                             i.startswith("//")] or []}
            )
            media_url.update(
                {"video_url": [self.parse_video_url(response) or ""]}
            )
            item_loader.add_value("media_url", media_url)
            content_list = response.css('.article>p::text').extract()
            content = self.remove_spaces_and_comments('\n'.join(content_list))
            item_loader.add_value("content", content)
            item_loader.add_css("abstract", 'meta[name="description"]::attr(content)')
            if not item_loader.get_collected_values("abstract"):
                # print("no abstract available")
                item_loader.add_value("abstract", content[:100] if len(content) > 100 else content)
            hot_dict = self.get_hot_statistics(response)
            item_loader.add_value("hot_data", hot_dict)
            yield item_loader.load_item()
        except Exception as e:
            self.logger.critical(msg=e)
            return None

    def parse_video_url(self, response):
        import re
        pattern = re.compile(r"SINA_TEXT_PAGE_INFO\['videoDatas0'\]=\[{\S+\}\]")
        origin_text = response.xpath('//*[@id="article"]/script/text()').extract_first()
        # 没有视频链接script的网页不必获得链接信息
        if origin_text is None:
            return None
        # 去掉空字符
        modified = re.sub("\\s", "", origin_text)
        # 切片，取SINA_TEXT_PAGE_INFO中的内容
        useful_fragments = modified[re.search(pattern, modified).start():re.search(pattern, modified).end()]
        pattern_url = re.compile(r'url:\'https?://video\.sina\.com\.cn/.*?\'')
        pattern_str = pattern_url.findall(useful_fragments)[0]
        return pattern_str.replace("url:", "").replace("'", "") or None

    def get_hot_statistics(self, response):
        import requests
        comment_url = r"http://comment.sina.com.cn/page/info?version=1&format=json&channel={}&newsid={}"
        # 评论地址变量：可以从新闻详情页sudameta获取
        metadatas = response.css('meta[name="sudameta"]::attr(content)').extract()
        temp_list = ';'.join(metadatas).split(';')
        temp_dict = {i[:i.index(':')].strip(): i[i.index(':') + 1:] for i in temp_list}
        channel = temp_dict.get('comment_channel')
        newsid = temp_dict.get('comment_id')
        if channel and newsid:
            req = requests.get(url=comment_url.format(channel, newsid), headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36",
            })
            content = req.json()
            if content.get('result') and content.get('result') and content.get('result').get('status').get('code') == 0:
                if content['result'].get('count'):
                    comment_num = content.get('result').get('count').get('thread_show')
                    participate_count = content.get('result').get('count').get('total')
                    return {
                        "comment_num": comment_num,
                        "participate_count": participate_count
                    }
            self.logger.warning("返回值错误，无法获取")
            return {
                "comment_num": "",
                "participate_count": ""
            }
        else:
            self.logger.warning("channel 或 newsid错误，无法获取api数据")
            return {
                "comment_num": "",
                "participate_count": ""
            }

    def remove_spaces_and_comments(self, repl_text):
        import re
        repl_text = re.sub(r'\s+', repl="", string=repl_text)
        repl_text = re.sub(r'\u3000', repl="", string=repl_text)
        return re.sub(r'<!--\S+-->', repl="", string=repl_text)
