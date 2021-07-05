import os
import sys
import random

from urllib.request import Request
from urllib.request import urlopen
from pathlib import Path


def is_ipv4(ip_addr):
    ip_group = str(ip_addr).split('.')

    if len(ip_group) != 4:
        return False

    for group in ip_group:
        if not group.isdigit():
            return False

        if 0 > int(group) > 255:
            return False

    return True


def download(url, download_path):
    # use a browser user agent in order to not be blocked by some sites that block urllib's ua
    request = Request(url, headers={'User-Agent': user_agent()})
    #request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0'})
    response = urlopen(request)
    write_file(response.read(), download_path, 'wb')
    return download_path


def user_agent():
    ua = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
        'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2)',
        'Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.116 Safari/537.36',
        'Mozilla/5.0 (Linux; Android 8.0.0; SM-G960F Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.84 Mobile Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0'
    ]
    return ua[random.randrange(len(ua))]


def write_file(content, path, write_mode):
    try:
        file = open(path, write_mode)
        file.write(content)
    finally:
        file.close()
    return path


def create_dir(path):
    if len(path) == 0:
        return False
    if not "/" in path:
        return False
    if not os.path.exists(path):
        try:
            os.makedirs(path)
            return True
        except FileExistsError:
            return True