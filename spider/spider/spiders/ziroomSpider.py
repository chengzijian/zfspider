# -*- coding: utf-8 -*-
"""
Created on Wed Jun 28 09:59:31 2017

@author: zhanglu01
"""

from items import HouseItem
from bs4 import BeautifulSoup

import scrapy
# from scrapy.spiders import CrawlSpider,Rule
# from scrapy.linkextractors import LinkExtractor
import config
import re
import sys
from scrapy_splash import SplashRequest

reload(sys)
sys.setdefaultencoding('utf-8')


class ZiroomSpider(scrapy.Spider):
    # 必须定义
    name = "ShanghaiHR"

    # 自定义配置
    custom_settings = {
        # item处理管道
        'ITEM_PIPELINES': {
            'spider.pipelines.DuplicatesPipeline': 1,
            'spider.pipelines.SavePipeline': 2,
        },
    }

    # 初始urls
    start_urls = [
        {
            # 链家
            'urls': ['http://sh.lianjia.com/zufang/%s/k1000to6000l2l3' % m
                     for m in ['pudong' , 'minhang', 'xuhui', 'zhabei', 'changning', 'jingan', 'huangpu']],
            'type': 'lianjia'
        },
        {
            # 自如
            'urls': ['http://sh.ziroom.com/z/nl/%s-%s-%s-u2.html?p=1' % (m, n, o)
                     for m in ['z1', 'z2', 'z6']
                     for n in ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']
                     for o in ['d310101', 'd310104', 'd310105', 'd310106', 'd310108', 'd310112', 'd310115']],
            'type': 'ziru'
        },
        {
            # 58
            'urls': ['http://sh.58.com/pinpaigongyu/pn/%s/?minprice=0_4500&fangshi=1&bedroomnum=2&PGTID=0d3111f6-0000-2ab8-3a9a-bb77983dd20e&ClickID=1' % n
                for n in range(1, 16)],
            'type':'58'
        }
    ]

    def start_requests(self):
        for parser in self.start_urls:
            for url in parser['urls']:
                if parser['type'] == '58':
                    yield SplashRequest(url, self.parse58, args={'wait': 0.5}, headers=config.WUBA_REQUEST_HEADERS)
                elif parser['type'] == 'ziru':
                    yield SplashRequest(url, self.parse, args={'wait': 0.5}, headers=config.ZIRU_REQUEST_HEADERS)
                elif parser['type'] == 'lianjia':
                    yield SplashRequest(url, self.parseLJ, args={'wait': 0.5}, headers=config.LIANJIA_REQUEST_HEADERS)

    def parseLJ(self, response):
        for li in response.xpath('//*[@id="house-lst"]/li'):
            house_item = HouseItem()
            try:
                house_item['title'] = li.xpath('div[2]/div[1]/div[1]/a/span/text()').extract()[0]
            except IndexError:
                house_item['title'] = ''

            try:
                detail_page_link = "http://sh.lianjia.com%s" % li.xpath('div[2]/h2/a/@href').extract()[0]
                house_item['link'] = detail_page_link
            except IndexError:
                house_item['link'] = ''

            try:
                house_item['area'] = li.xpath('div[2]/div[1]/div[1]/span[2]/text()').extract()[0].replace("平", "")
            except IndexError:
                house_item['area'] = ''

            try:
                house_item['rooms'] = li.xpath('div[2]/div[1]/div[1]/span[1]/text()').extract()[0]
            except IndexError:
                house_item['rooms'] = ''

            try:
                house_item['price'] = li.xpath('div[2]/div[2]/div[1]/span/text()').extract()[0]
            except IndexError:
                house_item['price'] = ''

            try:
                house_item['time_unit'] = re.findall(".*?(/.*).*", li.xpath('div[2]/div[2]/div[1]/text()').extract()[1])[0].replace("/", "")
            except IndexError:
                house_item['time_unit'] = ''

            try:
                house_item['district'] = li.xpath('div[2]/h2/a/text()').extract()[0]
            except IndexError:
                house_item['district'] = ''

            house_item['rentType'] = '整'
            if detail_page_link:
                request = scrapy.Request(detail_page_link, callback=self.parse_lianjia_detail_item, headers=config.LIANJIA_REQUEST_HEADERS)
                request.meta['house_item'] = house_item
                yield request

            # 请求下一页数据
            html = BeautifulSoup(response.text)
            results_next_page = html.find("a", gahref="results_next_page")
            if results_next_page:
                new = str(results_next_page)
                relink = r'[a-zA-z]+="/[^\s]*(?=")'
                link = str(re.findall(relink, new)[0]).replace('href="/', '')
                if link:
                    next_page_link = "http://sh.lianjia.com/%s" % link
                    print next_page_link
                    yield SplashRequest(next_page_link, self.parseLJ, args={'wait': 0.5}, headers=config.LIANJIA_REQUEST_HEADERS)

    def parse_lianjia_detail_item(self, response):
        house_item = response.meta['house_item']

        try:
            house_item['lng'] = response.xpath('//*[@id="zoneMap"]/@longitude').extract()[0]
        except IndexError:
            house_item['lng'] = ''
        try:
            house_item['lat'] = response.xpath('//*[@id="zoneMap"]/@latitude').extract()[0]
        except IndexError:
            house_item['lat'] = ''

        return house_item

    def parse58(self, response):
        html = BeautifulSoup(response.text)
        house_list = html.select(".list > li")

        for house in house_list:
            house_title = house.select("h2")[0].string.encode("utf8")
            house_url = "http://sh.58.com" + house.select("a")[0]["href"]
            house_info_list = house_title.split()

            house_item = HouseItem()
            house_item['title'] = house_title
            money = house.select(".money")[0].select("b")[0].string.encode("utf8")
            if "-" in money:
                money = money.split("-")[1]
            house_item['price'] = money
            house_item['link'] = house_url
            house_item['time_unit'] = '每月'
            # 如果第二列是公寓名则取第一列作为地址
            if "公寓" in house_info_list[1] or "青年社区" in house_info_list[1]:
                house_item['rentType'] = '直'
                house_location = house_info_list[0]
            else:
                house_location = house_info_list[1]
                if "合租" in house_title:
                    house_item['rentType'] = '合'
                elif "整租" in house_title:
                    house_item['rentType'] = '整'
                else:
                    house_item['rentType'] = ''

            house_item['floorLoc'] = ''
            house_item['floorTotal'] = ''
            house_item['heatingType'] = ''
            house_item['nearestSubWayDist'] = ''
            house_item['confStatus'] = ''
            if house_url:
                request = scrapy.Request(house_url, callback=self.parse_58_detail, headers=config.WUBA_REQUEST_HEADERS)
                request.meta['house_item'] = house_item
                yield request


    def parse_58_detail(self, response):
        html = BeautifulSoup(response.text)
        house_item = response.meta['house_item']
        for tag in html.find_all("script"):
            relink = r"(?<=____json4fe.lon = ').*(?=';)"
            lon = re.findall(relink, tag.text)
            relink = r"(?<=____json4fe.lat = ').*(?=';)"
            lat = re.findall(relink, tag.text)
            if lon and lat:
                house_item['lng'] = lon[0]
                house_item['lat'] = lat[0]
                break

        list = html.select("[class~=house-info-list]")
        if len(list) > 0:
            for tag in list:
                for span in tag.select("li"):
                    if "面积" in span.text:
                        try:
                            house_item['area'] = re.findall("[\s\S]*?(\d+(?:\.\d+)?)", span.select("span")[0].text)[0]
                        except IndexError:
                            house_item['area'] = ''
                    elif "厅室" in span.text:
                        try:
                            house_item['rooms'] = span.select("span")[0].text.split()[0]  # 厅室
                        except IndexError:
                            house_item['rooms'] = ''

                        try:
                            house_item['direction'] = span.select("span")[0].text.split()[1]  # 朝向
                        except IndexError:
                            house_item['direction'] = ''

                    elif "楼层" in span.text:
                        try:
                            floors = span.select("span")[0].text.split()[0].split("/")
                            try:
                                # 房间所在楼层
                                house_item['floorLoc'] = floors[0]
                            except IndexError:
                                house_item['floorLoc'] = ''

                            try:
                                # 大楼总层数
                                house_item['floorTotal'] = floors[1]
                            except IndexError:
                                house_item['floorTotal'] = ''

                        except IndexError:
                            house_item['floorLoc'] = ''
                            house_item['floorTotal'] = ''
                    elif "地址" in span.text:
                        try:
                            house_item['district'] = span.select("span")[0].text
                        except IndexError:
                            house_item['district'] = ''
                            # elif "交通" in span.text:
                            #    print span.select("span")[0].text
        else:
            try:
                house_item['area'] = re.findall("[\s\S]*?(\d+(?:\.\d+)?)", html.select("[class~=detailArea]")[0].text)[0]
            except IndexError:
                house_item['area'] = ''

            try:
                house_item['rooms'] = html.select("[class~=detailHX]")[0].text.replace("户型：", "")
            except IndexError:
                house_item['rooms'] = ''

            house_item['floorLoc'] = ''
            house_item['floorTotal'] = ''
            house_item['direction'] = ''  # 朝向
            house_item['district'] = ''

        house_item['halls'] = ''
        house_item['confGen'] = ''
        house_item['confType'] = ''
        house_item['privateBathroom'] = '0'
        house_item['privateBalcony'] = '0'
        return house_item


    def parse_detail_item(self, response):
        house_item = response.meta['house_item']
        try:
            house_item['title'] = response.xpath('/html/body/div[3]/div[2]/div[1]/h2/text()').extract()[0].strip()
        except IndexError:
            house_item['title'] = ''
        house_item['link'] = response.url
        try:
            house_item['price'] = re.sub('\D', '', response.xpath(
                '/html/body/div[3]/div[2]/div[1]/p/span[2]/span[1]/text()').extract()[0])
        except IndexError:
            house_item['price'] = ''
        try:
            house_item['area'] = re.findall("面积：[\s\S]*?(\d+(?:\.\d+)?).*㎡.*",
                                            response.xpath('/html/body/div[3]/div[2]/ul/li[1]/text()').extract()[0])[0]
        except IndexError:
            house_item['area'] = ''
        try:
            house_item['rooms'] = \
            re.findall(".*户型： (\d+)室.*", response.xpath('/html/body/div[3]/div[2]/ul/li[3]/text()').extract()[0])[0]
        except IndexError:
            house_item['rooms'] = ''
        try:
            house_item['halls'] = \
            re.findall(".*室(\d+)厅.*", response.xpath('/html/body/div[3]/div[2]/ul/li[3]/text()').extract()[0])[0]
        except IndexError:
            house_item['halls'] = ''
        try:
            house_item['lng'] = response.xpath('//*[@id="mapsearchText"]/@data-lng').extract()[0]
        except IndexError:
            house_item['lng'] = ''
        try:
            house_item['lat'] = response.xpath('//*[@id="mapsearchText"]/@data-lat').extract()[0]
        except IndexError:
            house_item['lat'] = ''
        try:
            house_item['direction'] = re.sub('朝向： ', '',
                                             response.xpath('/html/body/div[3]/div[2]/ul/li[2]/text()').extract()[0])
        except IndexError:
            house_item['direction'] = ''
        try:
            house_item['confGen'] = \
            re.findall(".*?(\d+\.?\d*).*", response.xpath('/html/body/div[3]/div[2]/p/a/span/text()').extract()[0])[0]
        except IndexError:
            house_item['confGen'] = ''
        try:
            house_item['confType'] = \
            re.findall(".*?\d+\.?\d* *(.*)$", response.xpath('/html/body/div[3]/div[2]/p/a/span/text()').extract()[0])[0]
        except IndexError:
            house_item['confType'] = ''
        try:
            house_item['privateBathroom'] = '1' if \
            response.xpath('/html/body/div[3]/div[2]/p/span[@class="toilet"]/text()').extract()[0] else '0'
        except IndexError:
            house_item['privateBathroom'] = '0'
        try:
            house_item['privateBalcony'] = '1' if \
            response.xpath('/html/body/div[3]/div[2]/p/span[@class="balcony"]/text()').extract()[0] else '0'
        except IndexError:
            house_item['privateBalcony'] = '0'
        try:
            house_item['district'] = \
            re.findall(".*?\[(.+?) .*", response.xpath('/html/body/div[3]/div[2]/div[1]/p/span[1]/text()').extract()[0])[0]
        except IndexError:
            house_item['district'] = ''
        return house_item


    def parse(self, response):
        for li in response.xpath('//*[@id="houseList"]/li'):
            if "clearfix zry" not in li.xpath('@class').extract():
                house_item = HouseItem()
                try:
                    house_item['time_unit'] = re.findall(".*\((.+)\).*", li.xpath('div[3]/p[1]/span/text()').extract()[0])[
                        0]
                except IndexError:
                    house_item['time_unit'] = ''
                try:
                    house_item['rentType'] = li.xpath('div[2]/div/p[1]/span[4]/text()').extract()[0]
                except IndexError:
                    house_item['rentType'] = ''
                try:
                    house_item['floorLoc'] = \
                    re.findall("^(\d+)/.*", li.xpath('div[2]/div/p[1]/span[2]/text()').extract()[0])[0]
                except IndexError:
                    house_item['floorLoc'] = ''
                try:
                    house_item['floorTotal'] = \
                    re.findall(".*/(\d+).*$", li.xpath('div[2]/div/p[1]/span[2]/text()').extract()[0])[0]
                except IndexError:
                    house_item['floorTotal'] = ''
                try:
                    for span in li.xpath('div[2]/p/span[2]/span[@class="subway"]'):
                        if span.xpath('text()').extract()[0].find('暖') == 1 or span.xpath('text()').extract()[0].find(
                                '空调') == 1:
                            house_item['heatingType'] = span.xpath('text()').extract()[0]
                            break
                except IndexError:
                    house_item['heatingType'] = ''

                try:
                    house_item['nearestSubWayDist'] = \
                    re.findall(".*?(\d+)米.*", li.xpath('div[2]/div/p[2]/span/text()').extract()[0])[0]
                except IndexError:
                    house_item['nearestSubWayDist'] = ''
                try:
                    house_item['confStatus'] = '0' if li.xpath('div[1]/a/img/@src').extract()[0].find(
                        'defaultPZZ') >= 0 else '1'
                except IndexError:
                    house_item['confStatus'] = ''

                detail_page_link = li.xpath('div[2]/h3/a/@href').extract()[0]
                if detail_page_link:
                    detail_page_link = detail_page_link if detail_page_link.find(
                        'www') >= 0 else 'http://' + detail_page_link
                    detail_page_link = detail_page_link if detail_page_link.find(
                        'http') >= 0 else 'http:' + detail_page_link
                    request = scrapy.Request(detail_page_link, callback=self.parse_detail_item, headers=config.ZIRU_REQUEST_HEADERS)
                    request.meta['house_item'] = house_item
                    yield request

        # 请求下一页数据
        if "next" in response.xpath('//*[@id="page"]/a/@class').extract():
            current_page_link = response.url
            if re.match('.*/z/nl/z[1|2|6]-r\d-.+?\.html\?p=\d+$', current_page_link):
                current_page_p = int(re.findall(".*\?p=(\d+).*", current_page_link)[0]) + 1
                current_page_prefix = re.findall("^(.+\?p=).*", current_page_link)[0]
                next_page_link = current_page_prefix + str(current_page_p)
                yield SplashRequest(next_page_link, self.parse, args={'wait': 0.5}, headers=config.ZIRU_REQUEST_HEADERS)
