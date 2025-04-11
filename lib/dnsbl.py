""" DNS Response Policy Zone Generator """

__version__ = '1.1.4'

import os
import re
import random
import stat
import shutil
import string
import subprocess
import logging

from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse

CFG = ConfigParser()
CFG_FILE = 'etc/dns-bl.ini'
CFG_GLOBAL = 'global'
CFG_0_0_0_0 = '0.0.0.0 '
CFG_127_0_0_1 = '127.0.0.1 '
CFG_DATE_FORMAT = '%Y%m%d'
LOG = logging.getLogger('dns-bl')


def main():
    try:
        init()
        block_lists()
        response_policy_file()
    except OSError as e:
        LOG.error(e)
        return 1
    else:
        return 0


def home():
    dnsbl_home = None
    try:
        dnsbl_home = os.environ['DNSBL_HOME']
    except KeyError as e:
        LOG.error('DNSBL_HOME environment variable not found')
        raise SystemExit(1) from e
    if not dnsbl_home:
        LOG.error('DNSBL_HOME environment variable is empty')
        raise SystemExit(1)
    if not dnsbl_home.startswith('/'):
        LOG.error('DNSBL_HOME must be an absolute path')
        raise SystemExit(1)

    return dnsbl_home


def init():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s '
               + '%(levelname)-8s '
               + '%(message)s',
        datefmt='%d-%m-%Y %H:%M:%S',
        handlers=[
            logging.FileHandler('last.log')
        ]
    )
    cfg_file_path = os.path.join(home(), CFG_FILE)
    try:
        with open(cfg_file_path, encoding='utf-8') as file:
            CFG.read_file(file)
    except FileNotFoundError as e:
        LOG.warning(e.strerror.lower())
        generate_default_config()
        LOG.info('a default configuration file was generated at %s',
                 cfg_file_path)
    else:
        CFG.read(cfg_file_path, 'utf8')

    if CFG.has_section(CFG_GLOBAL):
        for section in CFG.sections():
            if section == CFG_GLOBAL and len(CFG.options(CFG_GLOBAL)) == 0:
                LOG.error('configuration: section [%s] has not options',
                          CFG_GLOBAL)
                raise SystemExit(1)
    else:
        LOG.error('section [%s] not found', CFG_GLOBAL)
        raise SystemExit(1)

    if os.path.isdir(run_dir()):
        if not skip_block_list_download():
            shutil.rmtree(run_dir())

    create_directories(run_dir())


def block_lists():
    if skip_block_list_download():
        LOG.info('skipping download and using existing files')
        return
    for section in CFG.sections():
        if section == CFG_GLOBAL:
            continue
        if CFG.get(section, 'enabled').lower() == 'yes':
            uri = CFG.get(section, 'url')
            try:
                url = urlparse(uri)
            except ValueError as e:
                LOG.warning('skipping %s: %s', uri, e)
                continue
            # replace some filename unfriendly characters with dash
            provider = re.sub('[^A-Za-z0-9._-]', '-', section)
            if url.scheme in ['http', 'https']:
                download_filename = os.path.join(
                    run_dir(),
                    block_list_filename(provider,
                                        CFG.get(section, 'categories')))
                download(uri, download_filename)
            if url.scheme == 'file':
                shutil.copy(
                    url.path,
                    os.path.join(run_dir(),
                                 block_list_filename(provider,
                                                     CFG.get(section,
                                                             'categories'))))
            if url.scheme == 'rsync':
                for category in CFG.get(section, 'categories').split(','):
                    category = category.strip()
                    subprocess.call([
                        url.scheme,
                        '-rlD',
                        f'{uri}/dest/{category}/domains',
                        os.path.join(
                            run_dir(),
                            block_list_filename(provider, category))])


def response_policy_file():
    """ Generate response policy zone file. """

    domains = filter_domains()
    if domains:
        zone_file = CFG.get(CFG_GLOBAL, 'rpz_file')
        if os.path.isfile(zone_file):
            os.remove(zone_file)
        with open(zone_file, 'a', encoding='utf-8') as file:
            file.write(zone_header().strip() + '\n')
            for domain in domains:
                record = domain + '\n'
                file.write(record)
            set_permissions(zone_file)
    else:
        LOG.info('nothing to do')


def generate_default_config():
    CFG[CFG_GLOBAL] = {
        'rpz_file': os.path.join(home(), 'rpz.db'),
        'redirect': 'IN CNAME .',
        'whitelist_file_prefix': 'whitelist_',
        'zone_serial_form': 'incremental',
        'skip_block_list_download': 'false',
        'run_dir': '/run/dns-bl'
    }

    cfg_file_path = os.path.join(home(), CFG_FILE)
    create_directories(str(Path(cfg_file_path).parent.absolute()))
    with open(cfg_file_path, 'w', encoding='utf-8') as file:
        CFG.write(file)


def create_directories(path):
    """ Create all directories specified in path. """

    if not path:
        LOG.error('cannot create directory: "path" is not defined')
        raise SystemExit(1)
    if not os.path.isabs(path):
        LOG.error('%s: must be an absolute path', path)
        raise SystemExit(1)
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except FileExistsError:
            return True
        except PermissionError as e:
            LOG.error('%s: %s', path, e)
            raise SystemExit(1) from e

    return True


def block_list_filename(provider, category):
    return provider + '-' + category + '-' + rand()


def rand():
    """ Generate a four-character random string. """

    return ''.join(
        random.SystemRandom().choice(
            string.ascii_lowercase + string.ascii_uppercase + string.digits
        ) for _ in range(4)
    )


def download(url, download_path):
    try:
        request = Request(url, headers={'User-Agent': user_agent()})
        with urlopen(request) as response:
            with open(download_path, 'wb') as file:
                file.write(response.read())
    except HTTPError as e:
        LOG.error('%s %s while downloading %s', e.code, e.reason, url)
    except URLError as e:
        LOG.error('%s while downloading %s', e.reason, url)


def user_agent():
    """ Use a browser user agent as some sites block urllib's ua. """

    db = os.path.join(Path(home()), 'var/db/ua.db')
    with open(db, 'r', encoding='utf-8') as file:
        ua = file.readlines()

    return ua[random.randrange(len(ua))].strip()


def filter_domains():
    """ Filter downloaded domains. """

    redirect = CFG.get(CFG_GLOBAL, 'redirect')
    white_list = whitelist()
    domains = set()
    files = os.listdir(run_dir())
    for file in files:
        file_path = os.path.join(run_dir(), file)
        if os.path.isfile(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                try:
                    lines = file.readlines()
                except UnicodeDecodeError as e:
                    # bypass some weird characters in source
                    LOG.info('in %s: %s', file, e.reason)
                else:
                    for line in lines:
                        record = valid_record(line)
                        if not record:
                            continue
                        if record in white_list:
                            continue
                        domains.add(f'{record} {redirect}')
    LOG.info('%s records', len(domains))

    return domains


def valid_record(line):
    if not line.strip():
        return None
    record = sanitize(line.strip())
    if not valid(record):
        return None

    return record


def sanitize(line):
    """ Remove whitespaces and split by 0.0.0.0 or 127.0.0.1. """

    line = line.strip()
    line = line.replace('\t', ' ')
    if line.startswith(CFG_0_0_0_0) or line.startswith(CFG_127_0_0_1):
        line = line.split()[1]

    return line


def valid(record):
    """Any record in zone file is validated here.

       Rules:
         - only letters, numbers, dots, and dashes; cannot start/end with dash
         - multiple dashes allowed, including in position 3 and 4
         - maximum 250 characters without dots
         - label: 63 characters
    """

    if not re.match('^[A-Za-z0-9.-]*$', record):
        return False
    if is_ipv4(record):
        return False
    if record.endswith('.'):
        return False
    if '.' not in record:
        return False
    if record.startswith('-') or record.endswith('-'):
        return False
    if len(record.replace('.', '')) > 250:
        return False
    for label in record.split('.'):
        if len(label) > 63:
            return False

    return True


def is_ipv4(ip_addr):
    ip_group = str(ip_addr).split('.')
    if len(ip_group) != 4:
        return False
    for group in ip_group:
        if not group.isdigit():
            return False
        if 0 > int(group) > 254:
            return False

    return True


def set_permissions(zone_file):
    """ Set zone file permissions to parent directory's owner and group. """

    response_policy_dir_path = Path(zone_file)
    os_stat = os.stat(response_policy_dir_path.parent.absolute())
    os.chown(zone_file, os_stat.st_uid, os_stat.st_gid)
    os.chmod(
        zone_file,
        stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP
    )  # 640


def whitelist():
    """ Create list of domains to skip when generating \
        response policy zone file. """

    white_list = set()
    whitelist_path = os.path.join(Path(home(), 'etc'))
    whitelist_file_prefix = CFG.get(CFG_GLOBAL, 'whitelist_file_prefix')
    for _, _, files in os.walk(whitelist_path):
        for file in files:
            if file.startswith(whitelist_file_prefix):
                with open(os.path.join(whitelist_path, file),
                          encoding='utf-8') as file:
                    for line in file.readlines():
                        record = valid_record(line)
                        if record is not None:
                            white_list.add(record)

    return white_list


def zone_header():
    """ Generate a new zone header with an updated serial. """

    serial_db = os.path.join(Path(home()), 'var/db/serial.db')
    zone_header_db = os.path.join(Path(home()), 'var/db/zone_header.db')
    if not os.path.isfile(zone_header_db):
        LOG.error('zone header database missing, zone file not written')
        raise SystemExit(1)
    with open(zone_header_db, 'r', encoding='utf-8') as file:
        header = file.read()

    return header.replace('*', next_zone_serial(serial_db))


def next_zone_serial(db):
    """ Increment zone serial. """

    if not os.path.isfile(db):
        LOG.error('serial database missing, zone file not written')
        raise SystemExit(1)
    with open(db, 'r', encoding='utf-8') as file:
        serial = file.read()
    next_serial = format_zone_serial(serial)
    with open(db, 'w+', encoding='utf-8') as file:
        file.write(next_serial)

    return next_serial


def format_zone_serial(serial):
    if not serial:
        LOG.warning('empty serial database, resetting')
        if CFG.get(CFG_GLOBAL, 'zone_serial_form') == 'daily-incremental':
            serial = datetime.today().strftime(CFG_DATE_FORMAT) + '00'
        else:
            serial = '0'
    if CFG.get(CFG_GLOBAL, 'zone_serial_form') == 'daily-incremental':
        today = datetime.today().strftime(CFG_DATE_FORMAT)
        index = serial[len(today):]
        format_suffix = '%0' + str(len(index)) + 'g'
        next_index = format_suffix % (int(index) + 1)
        next_serial = today+next_index
    else:
        next_serial = str(int(serial) + 1)

    return next_serial


def skip_block_list_download():
    if CFG.get(CFG_GLOBAL, 'skip_block_list_download') == 'yes':
        return True

    return False


def run_dir():
    directory = CFG.get(CFG_GLOBAL, 'run_dir')
    if not directory:
        LOG.error('run_dir is not defined')
        raise SystemExit(1)
    if not os.path.isabs(directory):
        LOG.error('run_dir must be an absolute path')
        raise SystemExit(1)

    return os.path.join(Path(directory), 'lists')


if __name__ == '__main__':
    raise SystemExit(main())
