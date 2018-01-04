# -*- coding: utf-8 -*-
"""
Created on Wed Jun 28 12:18:34 2017

@author: zhanglu01
"""
from bs4 import BeautifulSoup
import re
import sys

reload(sys)
sys.setdefaultencoding('utf-8')


def checkProxyType(selfip):
    # ____json4fe
    html = BeautifulSoup(open('test1.html'), 'lxml')

    results_next_page = html.find("a", gahref="results_next_page")
    if results_next_page:
        new = '<a gahref="results_next_page" href="/zufang/pudong/d2k1000to6000l2l3">下一页</a>'

        relink = r'[a-zA-z]+="/[^\s]*(?=")'
        link = str(re.findall(relink, new)[0]).replace('href="/', '')
        if link:
            next_page_link = "http://sh.lianjia.com/%s" % link
            print next_page_link
            # yield SplashRequest(next_page_link, self.parseLJ, args={'wait': 0.5})

if __name__ == '__main__':
    checkProxyType(None)
