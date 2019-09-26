# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
import codecs
import datetime

from scrapy.exporters import JsonItemExporter


class JSONWithEncodingPipeline(object):
    def __init__(self):
        super().__init__()
        today = datetime.datetime.now()
        self.file = codecs.open(filename="./news_items/{}.json".format(int(today.timestamp())), mode="wb")
        self.exporter = JsonItemExporter(self.file, encoding="utf-8", ensure_ascii=False)
        self.exporter.start_exporting()

    def process_item(self, item, spider):
        self.exporter.export_item(item)
        return item

    def close_spider(self, spider):
        self.exporter.finish_exporting()
        self.file.close()


class ImageGettingPipeline(object):
    def process_item(self, item, spider):
        pass
