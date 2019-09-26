# -*- coding: utf-8 -*-
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from ..items import HotspotCrawlerItem, HotspotCrawlerItemLoader


class HuanqiuHotspotSpider(CrawlSpider):
    name = 'HuanqiuHotspot'
    allowed_domains = ['huanqiu.com', ]
    start_urls = ['http://www.huanqiu.com/', 'https://3w.huanqiu.com/']

    rules = (
        Rule(LinkExtractor(allow=r"https?://[^\s]*\.huanqiu\.com/\S+/[^\s]*\.html",
                           restrict_xpaths=['//a[not(contains(@href,"agt=8"))]', '//a[not(@rel) or not(@class)]'],
                           deny=(r"http://\S+\.\S+\.com/\S+\?agt=8", r"/pic/", r"/photo/")),
             callback='parse_item_huanqiu', follow=False),
    )

    def parse_item_huanqiu(self, response):
        print("parsing url %s" % response.url)
        item_loader = HotspotCrawlerItemLoader(item=HotspotCrawlerItem(), response=response)
        # url示例：https://3w.huanqiu.com/a/8b006e/7O2hOjqdbJm
        #          http://opinion.huanqiu.com/hqpl/2019-07/15093895.html
        try:
            import re
            item_loader.add_css("newsId", 'meta[name="contentid"]::attr(content)')
            item_loader.add_value("content_url", response.url)
            item_loader.add_value("source", "环球新闻网")
            title = response.css('head>title::text').extract_first()
            title = re.sub(r"_\S+_\S+", repl="", string=title)
            title = re.sub(r"_\S+", repl="", string=title)
            item_loader.add_value("title", title.strip())
            item_loader.add_css("source_from", 'meta[name="source"]::attr(content)')
            item_loader.add_css("publish_time",
                                '.la_t_a::text' or '.time> .item>span::text' or 'meta[name="publishdate"]::attr(content)')
            hot_data = self.get_hot_statistics(response)
            item_loader.add_value("hot_data", hot_data)
            keywords = list(
                set(response.css('meta[name="keywords"]::attr(content)').extract_first().split(',')))
            item_loader.add_value("keywords", [i for i in keywords if i.strip()])
            media_url = {}
            media_url.update(
                {"img_url": response.xpath('//*[@class="la_con"]//img//@src').extract() or []}
            )
            media_url.update(
                {"video_url": response.css('#vt-video>video::attr(src)').extract() or []}
            )
            content_list = response.css('.la_con>p::text').extract()
            content = '\n'.join(content_list)
            content = self.remove_spaces_and_comments(content)
            item_loader.add_value("content", content or "")
            item_loader.add_css("abstract", 'meta[name="description"]::attr(content)')
            if not item_loader.get_collected_values("abstract"):
                # print("no abstract available")
                item_loader.add_value("abstract", content[:100] if len(content) > 100 else content)
            item_loader.add_value("media_url", media_url)
            yield item_loader.load_item()
        except Exception as e:
            self.logger.critical(msg=e)
            return None

    def get_hot_statistics(self, response):
        import urllib, requests
        url = 'https://commentn.huanqiu.com/api/v2/async?a=comment&m=source_info&appid={}&sourceid={}&url={}'
        appid = 'e8fcff106c8f'
        sourceid = response.css('meta[name="contentid"]::attr(content)').extract_first()
        urlencoded = urllib.parse.quote(response.url)
        if sourceid:
            req = requests.get(url=url.format(appid, sourceid, urlencoded), headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36",
            })
            # print(req.url)
            content = req.json()
            # print(content)
            if content.get('code') == 22000:
                base_data = content.get('data')
                comment_num = base_data.get('n_comment') + base_data.get('d_comment')  # 把可能删掉的评论也算上
                # 参与数 = 评论数 + 回复数 + 总数
                participate_count = comment_num + base_data.get('n_reply') + base_data.get('d_reply') + base_data.get(
                    'n_active') + base_data.get('d_active')
                return {
                    "comment_num": comment_num,
                    "participate_count": participate_count
                }
            elif content.get('code') == 40400:
                return {
                    "comment_num": "该新闻未开放评论或无法获取",
                    "participate_count": "该新闻未开放评论或无法获取"
                }
            else:
                return {
                    "comment_num": "返回值错误，获取失败",
                    "participate_count": "返回值错误，获取失败"
                }
        else:
            return {
                "comment_num": "sourceid获取失败",
                "participate_count": "sourceid获取失败"
            }

    def remove_spaces_and_comments(self, repl_text):
        import re
        repl_text = re.sub(r'\s+', repl="", string=repl_text)
        repl_text = re.sub(r'\u3000', repl="", string=repl_text)
        return re.sub(r'<!--\S+-->', repl="", string=repl_text)
