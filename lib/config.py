import os
from pathlib import Path
from configparser import ConfigParser

cfg = ConfigParser()

def config():
    cfg.read(os.path.join(Path(os.environ['DNSBL_HOME']), 'conf/dns-bl.conf'))
    return cfg


def categories(section):
    return cfg.get(section, 'categories').split(',')


# configuration section name
def _global():
    return 'global'
