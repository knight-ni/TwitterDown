import os
import shutil
from http import cookiejar
from urllib import request
from ffmpy3 import FFmpeg
import glob


def clean_dir(downdir):
    if os.path.exists(downdir):
        shutil.rmtree(downdir)
    os.makedirs(downdir)


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


def merge(flist, exepath, downdir, filename):
    idxfile = downdir + '\\' + 'index.tmp'
    with open(idxfile, 'w') as f:
        f.write('file \'' + '\'\nfile \''.join(sorted(set(flist), key=lambda flist: flist[-8:-3])) + '\'')
    fullfile = downdir + '\\' + filename
    if os.path.exists(fullfile):
        os.remove(fullfile)
    else:
        ff = FFmpeg(executable=exepath, inputs={downdir + r'\index.tmp': '-f concat -safe 0 '},
                    outputs={fullfile: '-c copy '})
        ff.run()
        clean_file(downdir, ['ts', 'tmp'])
    return 0
