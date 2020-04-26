# -*- coding:'utf-8' -*-
import os
import sys
import json
import random
import shutil
import string
import time
from decimal import Decimal
from http import cookiejar
from urllib import request
from ffmpy3 import FFmpeg
import glob
from retrying import retry
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import requests
import threading
from bs4 import BeautifulSoup
from pyaria2 import Aria2RPC

fth = []


def clean_dir(downdir):
    if os.path.exists(downdir):
        shutil.rmtree(downdir)
    os.makedirs(downdir)


@retry
def cap_vedio(baseurl):
    links = []
    tarurl = 'https://www.savetweetvid.com/zh/downloader'
    mydata = {
        "url": baseurl
    }
    response = requests.post(tarurl, mydata).text
    bs = BeautifulSoup(response, features="lxml")
    trs = bs.find('tbody').findAll('tr')
    for tr in trs:
        tds = tr.findAll('td')
        info = []
        for td in tds:
            hf = td.find('a', href=True)
            if not hf:
                info.append(td.text.replace(' MB',''))
            else:
                info.append(hf['href'])
        links.append(info)
    return sorted(links, key=lambda x: x[3], reverse=True)[0]


@retry
def cap_m3u8(baseurl, chrome_path=os.getcwd() + '\\chromedriver.exe'):
    if not chrome_path or not os.path.exists(chrome_path):
        raise RuntimeError('Invalid Chrome Driver Path.')
    elif not baseurl:
        raise RuntimeError('URL Needed.')
    driver = None
    m3u8_add = None
    caps = DesiredCapabilities.CHROME
    caps['loggingPrefs'] = {'performance': 'ALL'}
    caps["pageLoadStrategy"] = "none"
    chrome_options = Options()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_experimental_option('w3c', False)
    chrome_options.add_argument('lang=zh_CN.UTF-8')
    chrome_options.add_argument('user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36"')
    chrome_options.add_argument('--headless')
    try:
        driver = webdriver.Chrome(executable_path=chrome_path,
                                  options=chrome_options, desired_capabilities=caps)
        driver.get(baseurl)

        while not m3u8_add:
            logs = [json.loads(log['message'])['message']['params'].get('request') for log in driver.get_log('performance')]
            m3u8_add = [x.get('url') for x in logs if x and 'm3u8' in x.get('url') in x.get('url')]
            try:
                driver.execute_script("window.scrollTo(0, 0)")
                #doc = driver.execute_script("return document.documentElement.outerHTML")
                element = driver.find_element_by_xpath('//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div/div/section/div/div/div[1]/div/div/div/article/div/div[3]/div[2]/div/div/div[2]/div/article/div/div/div/div[2]/div/div[2]/div/div/span/span')
                element.click()
            except Exception:
                pass
        return m3u8_add
    finally:
        driver.quit()


def m3u8_analyze(url):
    base_url = 'https://video.twimg.com'
    m3u8_dic = {}
    m3u8_add = None
    m3u8_txt = requests.get(url).text.split('\n')
    for idx, val in enumerate(m3u8_txt):
        if 'EXT-X-STREAM-INF' in val:
            res_txt = val.split(',')[1].split('=')[1].split('x')
            res_val = int(res_txt[0]) * int(res_txt[1])
            m3u8_dic[res_val] = m3u8_txt[idx + 1]
        elif 'EXTINF' in val:
            m3u8_add = url
    if not m3u8_add:
        m3u8_add = base_url + m3u8_dic[sorted(m3u8_dic.keys(), reverse=True)[0]]
    return m3u8_add


def get_ts_lst(myopener, url):
    tslst = []
    doc = get_resp(myopener, url)
    file_line = doc.split("\n")
    for index, line in enumerate(file_line):  # 第二层
        if "EXTINF" in line:  # 找ts地址并下载
            pd_url = url.rsplit("/")[:3]
            if "http" not in file_line[index + 1]:
                for el in file_line[index + 1].rsplit("/"):
                    if el:
                        pd_url.append(el)   # 拼出ts片段的URL
                tslst.append('/'.join(pd_url))
            else:
                tslst.append(file_line[index + 1])
    return tslst


def download_by_aria2(mydir, filename, link, thread, bufsize):
    exe_path = os.getcwd() + '\\aria2-win-64bit\\aria2c.exe'
    order = exe_path + ' -d ' + mydir + ' -o ' + filename + ' -s ' + str(thread) + ' -x ' + str(thread) + ' -k ' + bufsize + ' ' + link
    os.system(order)


@retry
def download_file(myopener, ts, fname, tout):
    ssize = 0
    res = ''
    try:
        res = requests.get(ts, stream=True)
        res.raise_for_status()
    except Exception as e:
        print(e)
    size = get_file_size(myopener, ts, tout)
    with open(fname, 'wb') as f:
        for chunk in res.iter_content(chunk_size=256000):
            if chunk:
                f.write(chunk)
                f.flush()
                ssize += len(chunk)
    if size and not int(size) == ssize:
        print('EOFError,Download Again...\n')
        raise
    return fname


def batch_down(myopener, url, mydir, cnt, tout, promode=False):
    ath = []
    if promode:
        backth = 2
    else:
        backth = 1
    if not os.path.exists(mydir):
        os.makedirs(mydir)
    else:
        tslst = get_ts_lst(myopener, url)
        for ts in tslst:
            topener = set_opener()
            while threading.active_count() > cnt:
                print('\r达到最大线程限制,等待已有线程完成!\n', end='')
                time.sleep(5)
                gen_process(len(fth), len(tslst))
            else:
                if len(ath) > cnt:
                    for x in ath:
                        if not x.isDaemon():
                            x.setDaemon(True)
                            x.start()
                else:
                    tsname = ts.split('/')[-1].split('.ts')[0] + '.ts'
                    filepath = mydir + '\\' + tsname
                    t = threading.Thread(target=download_file, args=(topener, ts, filepath, tout,))
                    ath.append(t)
                    fth.append(filepath)
        for x in ath:
            if not x.isDaemon():
                x.setDaemon(True)
                x.start()
        while threading.active_count() > backth:
            print('\r还剩一点工作,剩余线程数 %s\n' % str(threading.active_count()).zfill(2), end='')
            time.sleep(5)
        print('下载完成,开始合并...')
    return fth



def gen_process(cur, tot):
    pro = Decimal(cur*100/tot).quantize(Decimal("0.00"))
    nm = Decimal(0.01).quantize(Decimal("0.00"))
    if pro > 0:
        print(f'{pro-nm} %')


def ungzip(data):
    """Decompresses data for Content-Encoding: gzip.
    """
    from io import BytesIO
    import gzip
    buffer = BytesIO(data)
    f = gzip.GzipFile(fileobj=buffer)
    return f.read()


def undeflate(data):
    """Decompresses data for Content-Encoding: deflate.
    (the zlib compression is used.)
    """
    import zlib
    decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
    return decompressor.decompress(data) + decompressor.flush()


def set_opener():
    cookie = cookiejar.CookieJar()
    handler = request.HTTPCookieProcessor(cookie)
    myopener = request.build_opener(handler)
    #request.install_opener(myopener)
    return myopener


def clean_file(path, ext):
    for e in ext:
        for infile in glob.glob(os.path.join(path, '*.' + e)):
            os.remove(infile)


def get_file_size(myopener, url, tout):
    ts = myopener.open(url, timeout=tout)
    return ts.headers["Content-Length"]


def get_resp(myopener, url):
    response = myopener.open(url, timeout=3)
    data = response.read()
    if response.info().get('Content-Encoding') == 'gzip':
        data = ungzip(data)
    elif response.info().get('Content-Encoding') == 'deflate':
        data = undeflate(data)
    response.data = data
    doc = response.data.decode('utf-8')
    return doc


def merge(flist, downdir, fname, exepath=os.getcwd() + '\\ffmpeg-win64-static\\bin\\ffmpeg.exe'):
    if not exepath or not os.path.exists(exepath):
        raise RuntimeError('Invalid MMPEG Path.')
    idxfile = downdir + '\\' + 'index.tmp'
    with open(idxfile, 'w') as f:
        f.write('file \'' + '\'\nfile \''.join(flist) + '\'')
    fullfile = downdir + '\\' + fname
    if os.path.exists(fullfile):
        os.remove(fullfile)
    ff = FFmpeg(executable=exepath, inputs={idxfile: '-f concat -safe 0 '},
                outputs={fullfile: '-c copy '})
    ff.run()
    clean_file(downdir, ['ts', 'tmp'])
    return 0


def generate_random_str(randomlength):
    str_list = random.sample(string.digits + string.ascii_letters, randomlength)
    random_str = ''.join(str_list)
    return random_str


if __name__ == "__main__":
    opener = set_opener()
    play_url = ''
    link = cap_vedio(play_url)[3]
    download_dir = 'E:\\download_test'
    thread = 10
    timeout = 1
    bufsize = '1M'
    filename = generate_random_str(randomlength=20) + '.mp4'
    download_by_aria2(download_dir, filename, link, thread, bufsize)
    #m3u8_url = cap_m3u8(play_url)[0]
    #real_m3u8 = m3u8_analyze(m3u8_url)
    #flst = batch_down(opener, real_m3u8, download_dir, thread, timeout)
    #flst = batch_down(opener, real_m3u8, download_dir, thread, timeout, promode=True)
    #merge(flst, download_dir, filename)
