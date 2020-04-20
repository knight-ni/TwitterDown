# -*- coding:'utf-8' -*-
import os
import json
import random
import shutil
import string
import time
from http import cookiejar
from urllib import request
from ffmpy3 import FFmpeg
import glob
from retrying import retry
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import requests
import threading
import uuid

lth = []


def clean_dir(downdir):
    if os.path.exists(downdir):
        shutil.rmtree(downdir)
    os.makedirs(downdir)


def save_cookie():
    chrome_options = Options()
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(executable_path=os.getcwd() + "\\venv\\Lib\\site-packages\\chromedriver.exe",
                              options=chrome_options)
    try:
        driver.get('https://www.youku.com')
        time.sleep(2)
        driver.find_element_by_xpath('//*[@id="uerCenter"]/div[6]/div[1]/div/a/img[1]').click()
        time.sleep(1)
        logframe = driver.find_element_by_tag_name('iframe')
        time.sleep(1)
        driver.switch_to.frame(logframe)
        time.sleep(1)
        driver.find_element_by_xpath('//*[@id="login-form"]/div[1]/a').click()
        time.sleep(1)
        pwd_input = driver.find_element_by_id("fm-login-password")
        time.sleep(1)
        for p in 'P@nd@knight123':
            pwd_input.send_keys(p)
        time.sleep(1)
        user_input = driver.find_element_by_id("fm-login-id")
        time.sleep(1)
        for s in '18625157810':
            user_input.send_keys(s)
        time.sleep(1)
        login_btn = driver.find_element_by_class_name("fm-button" and "fm-submit" and "password-login")
        time.sleep(2)
        login_btn.click()
        time.sleep(2)
        dic = {}
        cookies = driver.get_cookies()
        for cookie in cookies:
            # print(cookie)
            key = cookie['name']
            value = cookie['value']
            dic[key] = value
    finally:
        driver.close()


def cap_m3u8(chrome_path, baseurl):
    driver = None
    m3u8_add = None
    caps = DesiredCapabilities.CHROME
    caps['loggingPrefs'] = {'performance': 'ALL'}
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
        try:
            element = WebDriverWait(driver, 5).until(
                ec.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div['
                                                          '1]/div/div/div/section/div/div/div/div['
                                                          '1]/div/div/div/article/div/div[3]/div[2]/div/div/div['
                                                          '2]/div/article/div/div/div/div[2]/div/div['
                                                          '2]/div/div/span/span'))
            )
            element.click()
        except Exception:
            pass
        while not m3u8_add:
            logs = [json.loads(log['message'])['message']['params'].get('request') for log in driver.get_log('performance')]
            m3u8_add = [x.get('url') for x in logs if x and 'm3u8' in x.get('url') and 'tag' in x.get('url')]
        return m3u8_add
    finally:
        driver.close()
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


def get_ts_lst(opener, url):
    tslst = []
    doc = get_resp(opener, url)
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


@retry
def download_file(opener, ts, fname, tout):
    ssize = 0
    res = ''
    if ts not in lth:
        lth.append(fname)
    try:
        res = requests.get(ts, stream=True)
        res.raise_for_status()
    except Exception as e:
        print(e)
    size = get_file_size(opener, ts, tout)
    with open(fname, 'wb') as f:
        for chunk in res.iter_content(chunk_size=4096000):
            if chunk:
                f.write(chunk)
                f.flush()
                ssize += len(chunk)
    if size and not int(size) == ssize:
        print('EOFError,Download Again...\n')
        raise EOFError
    return fname


def batch_down(opener, url, mydir, cnt, tout, promode=False):
    if promode:
        backth = 2
    else:
        backth = 1
    ath = []
    if not os.path.exists(mydir):
        os.makedirs(mydir)
    else:
        for ts in get_ts_lst(opener, url):
            while threading.active_count() >= cnt:
                for i in range(tout, 0, -1):
                    print('\r达到最大线程,进入等待计时,剩余 %s 秒!' % str(i).zfill(2), end='')
                    time.sleep(1)
                print('\r{:^5}'.format('开始下载！'))
                for x in ath:
                    x.join()
                ath = []
            else:
                tsname = ts.split('/')[-1].split('.ts')[0] + '.ts'
                filepath = mydir + '\\' + tsname
                t = threading.Thread(target=download_file, args=(opener, ts, filepath, tout,))
                t.start()
                print("Downloading File: " + filepath)
                ath.append(t)
        while threading.active_count() > backth:
            print('\r等待线程工作,剩余线程数 %s ' % str(threading.active_count()).zfill(2), end='')
            time.sleep(0.5)
        else:
            print('\n下载完成,开始合并...')
    return lth


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
    decompressobj = zlib.decompressobj(-zlib.MAX_WBITS)
    return decompressobj.decompress(data) + decompressobj.flush()


def set_opener():
    cookie = cookiejar.CookieJar()
    handler = request.HTTPCookieProcessor(cookie)
    opener = request.build_opener(handler)
    request.install_opener(opener)
    return opener


def clean_file(path, ext):
    for e in ext:
        for infile in glob.glob(os.path.join(path, '*.' + e)):
            os.remove(infile)


def get_file_size(opener, url, tout):
    ts = opener.open(url, timeout=tout)
    return ts.headers["Content-Length"]


def get_resp(opener, url):
    response = opener.open(url, timeout=3)
    data = response.read()
    if response.info().get('Content-Encoding') == 'gzip':
        data = ungzip(data)
    elif response.info().get('Content-Encoding') == 'deflate':
        data = undeflate(data)
    response.data = data
    doc = response.data.decode('utf-8')
    return doc


def merge(flist, exepath, downdir, fname):
    idxfile = downdir + '\\' + 'index.tmp'
    with open(idxfile, 'w') as f:
        f.write('file \'' + '\'\nfile \''.join(sorted(set(flist), key=lambda x: flist[-8:-3])) + '\'')
    fullfile = downdir + '\\' + fname
    if os.path.exists(fullfile):
        os.remove(fullfile)
    ff = FFmpeg(executable=exepath, inputs={idxfile: '-f concat -safe 0 '},
                outputs={fullfile: '-c copy '})
    ff.run()
    clean_file(downdir, ['ts', 'tmp'])
    return 0


def generate_random_str(randomlength):
    '''
    string.digits = 0123456789
    string.ascii_letters = 26个小写,26个大写
    '''
    str_list = random.sample(string.digits + string.ascii_letters, randomlength)
    random_str = ''.join(str_list)
    return random_str


if __name__ == "__main__":
    play_url = 'https://twitter.com/Mike28108429/status/1252143714777968641'
    download_dir = 'E:\\download_test'
    mmpeg_path = 'D:\\TwitterDown\\ffmpeg-win64-static\\bin\\ffmpeg.exe'
    chrome_path = 'D:\\TwitterDown\\chromedriver.exe'
    #promod = True
    thread = 20
    timeout = 1
    filename = generate_random_str(randomlength=20) + '.mp4'
    opener = set_opener()
    m3u8_url = cap_m3u8(chrome_path, play_url)[0]
    real_m3u8 = m3u8_analyze(m3u8_url)
    flst = batch_down(opener, real_m3u8, download_dir, thread, timeout)
    merge(flst, mmpeg_path, download_dir, filename)

