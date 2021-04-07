import sys

from scrapy import cmdline

sys.path.append("")

CRAWL_NAME = ""

if __name__ == '__main__':
    while CRAWL_NAME not in ('BaiduHotspot', 'FengHuangHotspot', 'HuanqiuHotspot'):
        CRAWL_NAME = input("Input name you want to crawl>> ")
    cmdline.execute(f"scrapy crawl {CRAWL_NAME}".split())
