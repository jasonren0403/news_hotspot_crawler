# -*- coding: utf-8 -*-
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from ..items import HotspotCrawlerItem, HotspotCrawlerItemLoader


class FengHuangHotspotSpider(CrawlSpider):
    name = 'FengHuangHotspot'
    allowed_domains = ['ifeng.com']
    start_urls = ['http://news.ifeng.com/', ]

    rules = (
        Rule(LinkExtractor(allow=r"^https?://news\.ifeng\.com/c/\w+$", restrict_css=r".content-14uJp0dk"), follow=False,
             callback='parse_items_fenghuang'),
    )

    def parse_items_fenghuang(self, response):
        print("parsing url %s" % response.url)
        # url 示例：http://news.ifeng.com/c/7o7LgnmZ0lS
        item_loader = HotspotCrawlerItemLoader(item=HotspotCrawlerItem(), response=response)
        try:
            item_loader.add_value("source", "凤凰网资讯")
            keywords = list(
                set(response.css('meta[name="keywords"]::attr(content)').extract_first().split(' ')))
            item_loader.add_value("keywords", keywords)
            item_loader.add_value("newsId", response.url.split('/')[-1])
            metadatas = self.get_metadatas(response)
            item_loader.add_css("publish_time", 'meta[name="og:time "]::attr(content)')
            if not item_loader.get_collected_values("publish_time"):
                item_loader.add_value("publish_time", metadatas.get('publish_time'))
            item_loader.add_value("title", metadatas.get("title") or "")
            item_loader.add_value("source_from", metadatas.get("source_from") or "")
            item_loader.add_value("content_url", metadatas.get("content_url") or response.url)
            item_loader.add_value("media_url", metadatas.get("media_url") or {})
            item_loader.add_value("content", metadatas.get("content") or "")
            hot_data = self.get_hot_stastistics(response, metadatas.get("comment_url"))
            item_loader.add_value("hot_data", hot_data or {})
            item_loader.add_value("abstract",
                                  metadatas.get("content") if len(metadatas.get("content")) < 100 else metadatas.get(
                                      "content")[:100] or "")
            yield item_loader.load_item()
        except Exception as e:
            self.logger.critical(msg=e)
            return None

    def get_metadatas(self, response):
        import re, json
        data_from = ""
        for each in response.css('head>script').extract():
            if "var allData" and "\"nav\"" in each:
                data_from = each
                break
        match = re.search(r"var\sadData\s=\s.+", data_from)
        if match:
            data_from = data_from[:match.start()]
            c = json.loads(data_from.lstrip("<script>").strip().lstrip("var allData = ").rstrip(";"), encoding='utf-8')
            base_data = c.get('docData')
            slide_data = c.get('slideData')
            if base_data or slide_data:
                image_urls = []
                video_urls = []
                content = ""
                publish_time = base_data.get('newsTime')
                if base_data.get('fhhAccountDetail'):
                    source_from = base_data.get('fhhAccountDetail').get('weMediaName') or "<default>凤凰网"
                else:
                    source_from = base_data.get('source') or "<default>凤凰网"
                title = base_data.get('title') or ""
                content_url = base_data.get('pcUrl') or response.url
                comment_url = base_data.get('commentUrl')
                if "ImagesInContent" in base_data:
                    for each in base_data.get('ImagesInContent'):
                        image_urls.append(each.get('url'))
                if "contentData" in base_data and base_data.get('contentData'):
                    for each in base_data['contentData']['contentList']:
                        if each.get('type') == 'text':
                            content = each['data'] or ""
                        elif each.get('type') == 'video':
                            video_urls.append(each['data'].get('playUrl') or "")
                        else:
                            print(each.get('type'))
                    content = self.deal_with_content(content)
                else:
                    content_list = []
                    for each in slide_data:
                        if each.get('type') == 'pic':
                            image_urls.append(each.get('url'))
                            content_list.append(each.get('description'))
                        else:
                            print(each.get('type'))
                    content_list = list(set(content_list))
                    content = '\n'.join(content_list) or ""
                return {
                    "title": title or "",
                    "source_from": source_from or "",
                    "content_url": content_url or "",
                    "comment_url": comment_url or "",
                    "publish_time": publish_time or "",
                    "media_url": {
                        "img_url": image_urls or [],
                        "video_url": video_urls or []
                    },
                    "content": content or ""
                }
        return {}

    def get_hot_stastistics(self, response, docUrl):
        import requests
        comment_url = r"http://comment.ifeng.com/get.php?docUrl={}&format=json&job=1&callback=callbackGetFastCommentCount".format(
            docUrl)
        # 评论地址：https://comment.ifeng.com/get.php?docUrl=ucms_7oAdVSVVdv7&format=json&job=1&callback=callbackGetFastCommentCount
        req = requests.get(url=comment_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36",
        })
        if req.status_code == requests.status_codes.codes.get('ok'):
            contents = req.json()
            if contents.get('allow_comment') == 1:
                comment_num = contents.get('count')
                participate_count = contents.get('join_count')
                return {
                    "comment_num": comment_num,
                    "participate_count": participate_count
                }
            else:
                return {
                    "comment_num": "当前新闻未开放评论功能",
                    "participate_count": ""
                }
        else:
            return {
                "comment_num": "api数据获取失败",
                "participate_count": "api数据获取失败"
            }

    def deal_with_content(self, repl_text):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(repl_text, "lxml")
        return '\n'.join(string for string in soup.stripped_strings) or ""
