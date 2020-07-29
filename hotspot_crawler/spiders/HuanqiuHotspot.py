# -*- coding: utf-8 -*-
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from ..items import HotspotCrawlerItem, HotspotCrawlerItemLoader


class HuanqiuHotspotSpider(CrawlSpider):
    name = 'HuanqiuHotspot'
    allowed_domains = ['huanqiu.com', ]
    start_urls = ['https://www.huanqiu.com/', 'https://3w.huanqiu.com/']

    rules = (
        Rule(LinkExtractor(allow=r"https://[0-9A-Za-z]+\.huanqiu\.com/article/[0-9A-Za-z]+"),
             callback='parse_item_huanqiu', follow=False),
    )

    def parse_item_huanqiu(self, response):
        self.logger.info("parsing url %s" % response.url)
        item_loader = HotspotCrawlerItemLoader(item=HotspotCrawlerItem(), response=response)
        # url示例：https://oversea.huanqiu.com/article/3zFei0GDscp
        try:
            import re
            item_loader.add_value("newsId", response.url.split('/')[-1])
            item_loader.add_value("content_url", response.url)
            item_loader.add_value("source", "环球新闻网")
            item_loader.add_css("title", '.t-container-title>h3::text')
            item_loader.add_css("source_from", '.source a::text')
            item_loader.add_css("publish_time", 'p.time::text')
            hot_data = self.get_hot_statistics(response)
            item_loader.add_value("hot_data", hot_data)
            keywords = list(
                set(response.css('meta[name="keywords"]::attr(content)').extract_first().split(',')))
            item_loader.add_value("keywords", [i for i in keywords if i.strip()])
            media_url = {}
            media_url.update(
                {"img_url": response.css('.pic-con img::attr(src)').extract() or []}
            )
            media_url.update(
                {"video_url": response.css('video::attr(src)').extract() or []}
            )
            content_list = response.css('article p::text').extract()
            content = '\n'.join(content_list)
            content = remove_spaces_and_comments(content)
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
        import requests, re
        appid = 'fLHTlMN2j3'
        title = response.css('.t-container-title>h3::text').extract_first()
        category = re.findall(r'(\w+\.huanqiu\.com)', response.url)
        if category:
            cat = category[0]
        else:
            self.logger.warn('Bad category item, return')
            return
        req = requests.post(url='https://api.comment.huanqiu.com/api/sourceInfo',
                            data={
                                "app_id": appid,
                                "article_id": response.url.split('/')[-1],
                                "article_url": response.url,
                                "category": cat,
                                "title": title,
                            },
                            headers={
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36",
                            })
        content = req.json()
        if content.get('code') == 2000:
            base_data = content.get('data')
            comment_num = base_data.get('comment_sum')
            participate_count = base_data.get('participation_sum')
            return {
                "comment_num": comment_num,
                "participate_count": participate_count
            }
        elif content.get('code') == 40400:
            self.logger.warning(f"[{response.url}] 该新闻未开放评论或无法获取")
            return {
                "comment_num": "",
                "participate_count": ""
            }
        else:
            self.logger.warning(f"[{response.url}] 返回值非正常 {content.get('code')}")
            return {
                "comment_num": "",
                "participate_count": ""
            }


def remove_spaces_and_comments(repl_text):
    import re
    repl_text = re.sub(r'\s+', repl="", string=repl_text)
    repl_text = re.sub(r'\u3000', repl="", string=repl_text)
    return re.sub(r'<!--\S+-->', repl="", string=repl_text)
