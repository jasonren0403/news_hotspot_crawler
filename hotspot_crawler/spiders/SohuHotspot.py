# -*- coding: utf-8 -*-
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from ..items import HotspotCrawlerItem, HotspotCrawlerItemLoader


class SohuHotspotSpider(CrawlSpider):
    name = 'SohuHotspot'
    allowed_domains = ['sohu.com']
    start_urls = ['https://news.sohu.com/', ]

    rules = (
        Rule(LinkExtractor(allow=r"^https?://www\.sohu\.com/a/\d{9,}_\d{6,}\S*$",
                           deny="picture/"), follow=False,
             callback='parse_items_sohu'),
    )

    def parse_items_sohu(self, response):
        import re
        # url 示例：http://www.sohu.com/a/325336334_162522
        self.logger.info("parsing url %s" % response.url)
        item_loader = HotspotCrawlerItemLoader(item=HotspotCrawlerItem(), response=response)
        try:
            title = response.css('head>title::text').extract_first()
            title = re.sub(r"_\S+", "", title)
            item_loader.add_value("title", title)
            item_loader.add_value("source", "搜狐新闻")
            item_loader.add_css("source_from", 'meta[name="mediaid"]::attr(content)')
            item_loader.add_css("publish_time", 'meta[itemprop="datePublished"]::attr(content)')
            item_loader.add_value("content_url", response.url)
            if not item_loader.get_collected_values("content_url"):
                item_loader.add_value("content_url", response.url)
            item_loader.add_value("newsId", re.sub(r"\?\w+=\w+", "", response.url.split('/')[-1]))
            # 由于网页中的元数据的部分关键词是重复的，故需要过滤处理一下
            item_loader.add_value("keywords", list(
                set(response.css('meta[name="keywords"]::attr(content)').extract_first().split(','))))
            media_url = {}
            media_url.update(
                {"img_url": response.css('.article>p>img::attr(src)').extract() or []}
            )
            media_url.update(
                {"video_url": ["请访问新闻链接以获得详情"] if response.css('#sohuplayer') else []}
            )
            item_loader.add_value("media_url", media_url)
            cnt_list = response.css('article>p::text').extract()
            content = '\n'.join(i.strip() for i in cnt_list)
            content = self.remove_spaces_and_comments(content.strip("责任编辑："))
            item_loader.add_value("content", content)
            item_loader.add_css("abstract", 'meta[name="description"]::attr(content)')
            if not item_loader.get_collected_values("abstract"):
                # print("no abstract available")
                item_loader.add_value("abstract", content[:100] if len(content) > 100 else content)
            hot_data = self.get_hot_statistics(response)
            item_loader.add_value("hot_data", hot_data)
            yield item_loader.load_item()
        except Exception as e:
            self.logger.critical(msg=e)
            return None

    def get_hot_statistics(self, response):
        import re, requests
        url = "http://apiv2.sohu.com/api/topic/load?source_id={}"
        id_temp = re.sub(r"\?\w+=\w+", "", response.url.split('/')[-1])
        source_id = 'mp_' + id_temp.split('_')[0]
        req = requests.get(url=url.format(source_id), headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36",
        })
        # print(req.url)
        needed_datas = req.json()
        # print(needed_datas)
        if needed_datas.get('msg') != 'FAIL' and needed_datas.get('jsonObject') is not None:
            comment_num = needed_datas.get('jsonObject').get('cmt_sum')
            participate_count = needed_datas.get('jsonObject').get('participation_sum')
            return {
                "comment_num": comment_num,
                "participate_count": participate_count
            }
        else:
            self.logger.warn(f"Api数据获取失败！received: {needed_datas}")
            return {
                "comment_num": "",
                "participate_count": ""
            }

    def remove_spaces_and_comments(self, repl_text):
        import re
        repl_text = re.sub(r'\s+', repl="", string=repl_text)
        repl_text = re.sub(r'\u3000', repl="", string=repl_text)
        return re.sub(r'<!--\S+-->', repl="", string=repl_text)
