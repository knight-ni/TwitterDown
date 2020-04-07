import re

from CommonLib import *
import os
from retrying import retry
import threading
import requests
import time
import json


class YouKuTsDown:
    def __init__(self, downdir):
        self.thread_num = 0
        self.opener = set_opener()
        self.lth = []
        clean_dir(downdir)


    def get_resp(self, url):
        response = self.opener.open(url, timeout=3)
        data = response.read()
        if response.info().get('Content-Encoding') == 'gzip':
            data = ungzip(data)
        elif response.info().get('Content-Encoding') == 'deflate':
            data = undeflate(data)
        response.data = data
        doc = response.data.decode('utf-8')
        return doc

    @retry
    def get_ts_address(self, url, quality, form):
        m3url = ''
        vid = re.findall(r'id_(.+)\.html.+', url)
        # 获取证书
        r = requests.get('http://log.mmstat.com/eg.js')
        start = len('window.goldlog=(window.goldlog||{});goldlog.Etag=\"')
        end = len('window.goldlog=(window.goldlog||{});goldlog.Etag=\"66C9FJlZrDYCAQFQU4AhkzO0')
        sert = r.text[start:end]

        param = {
            'vid': vid,
            'ccode': '0590',
            'client_ip': '192.168.1.1',
            'utid': '2py9FNCXjUcCAQFQU4APrwPf',
            'client_ts': '1547028409',
            'ckey': 'DIl58SLFxFNndSV1GFNnMQVYkx1PP5tKe1siZu/86PR1u/Wh1Ptd+WOZsHHWxysSfAOhNJpdVWsdVJNsfJ8Sxd8WKVvNfAS8aS8fAOzYARzPyPc3JvtnPHjTdKfESTdnuTW6ZPvk2pNDh4uFzotgdMEFkzQ5wZVXl2Pf1/Y6hLK0OnCNxBj3+nb0v72gZ6b0td+WOZsHHWxysSo/0y9D2K42SaB8Y/+aD2K42SaB8Y/+ahU+WOZsHcrxysooUeND'
        }

        headers = {
            'Accept-Encoding': 'identity',
            'Host': 'ups.youku.com',
            'Referer': 'http://v.youku.com',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36',
            'Connection': 'close'
        }

        now = time.time()
        nowint = int(now)
        nowstr = str(nowint)
        param['client_ts'] = nowstr
        param['utid'] = sert

        url = 'http://v.youku.com/ups/get.json?'
        r = requests.get(url, headers=headers, params=param)

        r_j = json.loads(r.text)
        streams = r_j.get('data').get('stream')

        for stream in streams:
            m3url = ''
            cdurl = ''
            m3u8_url = stream.get('m3u8_url')
            if form in m3u8_url and quality in m3u8_url:
                m3url = m3u8_url
            else:
                m3url = m3u8_url
            cdn_url = stream.get('segs')[0].get('cdn_url')
            if form in cdn_url:
                cdurl = cdn_url
        return [m3url, cdurl]


    def get_ts_lst(self, url):
        doc = self.get_resp(url)
        file_line = doc.split("\n")
        for index, line in enumerate(file_line):  # 第二层
            if "EXTINF" in line:  # 找ts地址并下载
                pd_url = url.rsplit("/")[:3]
                if "http" not in file_line[index + 1]:
                    for el in file_line[index + 1].rsplit("/"):
                            pd_url.append(el)   # 拼出ts片段的URL
                    yield '/'.join(pd_url)
                else:
                    yield file_line[index + 1]

    #@retry(wait_fixed=5)
    def download_file(self, ts, filename, tout):
        if ts not in self.lth:
            self.lth.append(filename)
        try:
            ts = self.opener.open(ts, timeout=tout)
        except Exception as e:
            print(e)
        size = ts.headers["Content-Length"]
        with open(filename, 'wb') as f:
            content = ts.read()
            if size and not size == str(len(content)):
                raise EOFError
            else:
                f.write(content)
                f.flush()
        return filename

    def batch_down(self, url, mydir, cnt, tout):
        lth = []
        if not os.path.exists(mydir):
            os.makedirs(mydir)
        else:
            for ts in self.get_ts_lst(url):
                while threading.active_count() >= cnt:
                    for i in range(5, -1, -1):
                        print('\r达到最大线程,进入等待计时,剩余 %s 秒!' % str(i).zfill(2), end='')
                        time.sleep(1)
                    print('\r{:^5}'.format('开始下载！'))
                    for l in lth:
                        l.join()
                    lth = []
                else:
                    tsname = ts.split('/')[4].split('.ts')[0] + '.ts'
                    filepath = mydir + '\\' + tsname
                    t = threading.Thread(target=self.download_file, args=(ts, filepath, tout,))
                    t.start()
                    print("Downloading File: " + filepath )
                    lth.append(t)
            while threading.active_count() > 1:
                print('\r等待线程工作,剩余线程数 %s ' % str(threading.active_count()).zfill(2), end='')
                time.sleep(5)
            else:
                print('\n下载完成,开始合并...')
        return 0

    def merge_file(self, exepath, downdir, filename):
        merge(self.lth, exepath, downdir, filename)


if __name__ == "__main__":
    down_load_dir = 'E:\\download_test'
    mmpegpath = 'D:\\Program Files (x86)\\YouKu\\YoukuClient\\nplayer64\\ffmpeg.exe'
    fmt = 'mp4'
    thread = 20
    timeout = 10
    filename = 'testfile.mp4'
    quality = 'hdv'
    vurl = [
         'https://v.youku.com/v_show/id_XMzc2NzcyMDc2.html?spm=a2hcb.12523958.m_9274_c_23571.d_4&s=3b285e307fb511e19194&scm=20140719.manual.9274.show_3b285e307fb511e19194'
         ]
    td = YouKuTsDown(down_load_dir)
    ul = td.get_ts_address(vurl[0], quality, fmt)
    if ul[1]:
        td.download_file(ul[1], down_load_dir + '\\' + filename, timeout)
    else:
        td.batch_down(ul[0], down_load_dir, thread, timeout)
        td.merge_file(mmpegpath, down_load_dir, filename)

