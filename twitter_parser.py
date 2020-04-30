import sys
import requests
from bs4 import BeautifulSoup
from decimal import Decimal


def savetweetvid(baseurl):
    links = []
    tarurl = 'https://www.savetweetvid.com/zh/downloader'
    mydata = {
        "url": baseurl
    }
    response = requests.post(tarurl, mydata).text
    bs = BeautifulSoup(response, features="lxml")
    body = bs.find('tbody')
    if not body:
        print('No URL Cathed.')
        sys.exit()
    else:
        trs = body.findAll('tr')
        for tr in trs:
            tds = tr.findAll('td')
            info = []
            for td in tds:
                hf = td.find('a', href=True)
                if not hf:
                    if 'MB' in td.text:
                        info.append(Decimal(td.text.replace(' MB', '')).quantize(Decimal('0.00')) * 1024)
                    elif 'KB' in td.text:
                        info.append(Decimal(td.text.replace(' KB', '')).quantize(Decimal('0.00')))
                    elif 'GB' in td.text:
                        info.append(Decimal(td.text.replace(' GB', '')).quantize(Decimal('0.00')) * 1024 * 1024)
                    else:
                        info.append(td.text)
                else:
                    info.append(hf['href'])
            links.append(info)
        linkdic = sorted(links, key=lambda x: x[2], reverse=True)[0][3]
    return linkdic


def twittervideodownloader(baseurl):
    links = []
    initurl = 'http://twittervideodownloader.com/'
    response = requests.get(initurl)
    cookie = response.headers['Set-Cookie']
    csrfmiddle = BeautifulSoup(response.text, features="lxml").find("input", attrs={"name": "csrfmiddlewaretoken"})['value']
    myhead = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": cookie,
        "Host": "twittervideodownloader.com",
        "Origin": "http://twittervideodownloader.com",
        "Referer": "http://twittervideodownloader.com/",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36"
    }
    mydata = {
        "csrfmiddlewaretoken": csrfmiddle,
        "tweet": baseurl
    }
    tarurl = 'http://twittervideodownloader.com/download'
    response = requests.post(url=tarurl, data=mydata, headers=myhead).text
    bs = BeautifulSoup(response, features="lxml")
    body = bs.findAll('a', attrs={"class": "expanded button small float-right"})
    if not body:
        print('No URL Cathed.')
        sys.exit()
    else:
        for x in body:
            myurl = x['href']
            lenth, width = myurl.split('/')[7].split('x')
            size = int(lenth) * int(width)
            links.append([size, myurl])
        linkdic = sorted(links, key=lambda x: x[0], reverse=True)[0][1]
    return linkdic


if __name__ == "__main__":
    myurl = 'https://twitter.com/Designer_Patric/status/1255102566754443271'
    twittervideodownloader(myurl)