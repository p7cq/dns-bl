import os
import sys
import random
import shutil
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


def download(url, save_path):
    # use a browser user agent in order to not be blocked by some sites that reject urllib's ua
    request = Request(url, headers={'User-Agent': user_agent()})
    response = urlopen(request)
    write_file(response.read(), save_path, 'wb')
    return save_path


def user_agent():
    ua = [
        'Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36'
    ]
    return ua[random.randrange(len(ua))]


def write_file(content, path, write_mode):
    try:
        file = open(path, write_mode)
        file.write(content)
    finally:
        file.close()
    return path
