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
from urllib.request import Request
from urllib.request import urlopen

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
    except Exception as e:
        LOG.error(str(e))
        return 1
    return 0


def home():
    dnsbl_home = None
    try:
        dnsbl_home = os.environ['DNSBL_HOME']
    except Exception:
        LOG.error('DNSBL_HOME environment variable not found')
        raise SystemExit(1)

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
        format='%(asctime)s ' +
               '%(levelname)-5.5s ' +
               '%(message)s',
        datefmt='%d-%m-%Y %H:%M:%S',
        handlers=[
            logging.FileHandler('last.log')
        ]
    )
    cfg_file_path = os.path.join(home(), CFG_FILE)
    try:
        CFG.read_file(open(cfg_file_path))
    except Exception:
        default_config()
        LOG.info('configuration file not found')
        LOG.info('default configuration was generated at ' +
                 cfg_file_path)
    CFG.read(cfg_file_path, 'utf8')

    if CFG.has_section(CFG_GLOBAL):
        for section in CFG.sections():
            if section == CFG_GLOBAL and len(CFG.options(CFG_GLOBAL)) == 0:
                LOG.error('configuration: section [' +
                          CFG_GLOBAL +
                          '] has not options')
                raise SystemExit(1)
    else:
        LOG.error('section [' + CFG_GLOBAL + '] not found')
        raise SystemExit(1)

    if os.path.isdir(run_dir()):
        if not skip_block_list_download():
            shutil.rmtree(run_dir())

    create_dirs(run_dir())


def block_lists():
    if skip_block_list_download():
        LOG.info('skipping download and using existing files')
        return

    for section in CFG.sections():
        if section == CFG_GLOBAL:
            continue

        if CFG.get(section, 'enabled').lower() == 'yes':
            uri = CFG.get(section, 'url')

            scheme = uri[0:uri.index(':')]
            # replace some filename unfriendly characters with underscore
            provider = re.sub('[^A-Za-z0-9._-]', '-', section)
            if scheme in ['http', 'https']:
                url = uri
                download_filename = os.path.join(
                    run_dir(),
                    block_list_filename(provider,
                                        CFG.get(section, 'categories')))
                try:
                    download(url, download_filename)
                except Exception as e:
                    LOG.info(e,
                             'exception caught while downloading [' +
                             section +
                             '] from ' +
                             url)

            if scheme in ['file']:
                url = uri[uri.index(':')+1:len(uri)]
                shutil.copy(
                    url,
                    os.path.join(run_dir(),
                                 block_list_filename(provider,
                                                     CFG.get(section,
                                                             'categories'))))

            if scheme in ['rsync']:
                url = uri
                for category in CFG.get(section, 'categories').split(','):
                    subprocess.call([
                        scheme,
                        '-rlD',
                        url + '/dest/' + category.strip() + '/domains',
                        os.path.join(
                            run_dir(),
                            block_list_filename(provider, category))])


def response_policy_file():
    domains = filter_domains()
    if len(domains) > 0:
        response_policy_file = CFG.get(CFG_GLOBAL, 'rpz_file')

        if os.path.isfile(response_policy_file):
            os.remove(response_policy_file)

        with open(response_policy_file, 'a') as file:
            file.write(zone_header().strip() + '\n')
            for domain in domains:
                record = domain + '\n'
                file.write(record)
            set_permissions(response_policy_file)
    else:
        LOG.info('nothing to do')


def default_config():
    CFG[CFG_GLOBAL] = {
        'rpz_file': os.path.join(home(), 'rpz.db'),
        'redirect': 'IN CNAME .',
        'whitelist_file_prefix': 'whitelist_',
        'zone_serial_form': 'incremental',
        'skip_block_list_download': 'false',
        'run_dir': '/run/dns-bl'
    }

    cfg_file_path = os.path.join(home(), CFG_FILE)

    create_dirs(str(Path(cfg_file_path).parent.absolute()))

    with open(cfg_file_path, 'w') as file:
        CFG.write(file)


def create_dirs(path):
    if len(path) == 0:
        return False
    if '/' not in path:
        return False
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except FileExistsError:
            return True
        except PermissionError:
            LOG.error('permission denied: ' + path)
            raise SystemExit(1)
    return True


def block_list_filename(provider, category):
    return provider + '-' + category + '-' + rand()


def rand():
    return ''.join(
        random.SystemRandom().choice(
            string.ascii_lowercase + string.ascii_uppercase + string.digits
        ) for _ in range(4)
    )


def download(url, download_path):
    request = Request(url, headers={'User-Agent': user_agent()})
    response = urlopen(request)
    write_file(response.read(), download_path, 'wb')
    return download_path


# use a browser user agent as some sites block urllib's ua
def user_agent():
    db = os.path.join(Path(home()), 'var/db/ua.db')

    with open(db, 'r') as file:
        ua = file.readlines()

    return ua[random.randrange(len(ua))].strip()


def filter_domains():
    redirect = CFG.get(CFG_GLOBAL, 'redirect')
    white_list = whitelist()
    domains = set()

    files = os.listdir(run_dir())
    for file in files:
        file_path = os.path.join(run_dir(), file)
        if os.path.isfile(file_path):
            lines = ()
            with open(file_path, 'r') as file:
                try:
                    lines = file.readlines()
                except UnicodeDecodeError as e:
                    LOG.info(e)
                    # bypass some weird characters in source
                    pass
                for line in lines:
                    record = valid_record(line)
                    if record is None:
                        continue
                    if record in white_list:
                        continue
                    domains.add(record + ' ' + redirect)

    LOG.info(str(len(domains)) + ' records added')

    return domains


def valid_record(line):
    if not line.strip():
        return None

    record = sanitize(line.strip())

    if not valid(record):
        return None

    return record


def sanitize(line):
    line = line.strip()
    line = line.replace('\t', ' ')
    if line.startswith(CFG_0_0_0_0) or line.startswith(CFG_127_0_0_1):
        line = line.split()[1]
    return line


# any record that makes it to RPZ file is validated here
# letters, numbers, dashes; cannot start/end with dash
# but: multiple dashes allowed, including in position 3 and 4
# 250 characters without dots
# label: 63 characters
def valid(record):
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


# change RPZ file permissions to parent directory's owner and group
def set_permissions(response_policy_file):
    response_policy_dir_path = Path(response_policy_file)
    os_stat = os.stat(response_policy_dir_path.parent.absolute())
    os.chown(response_policy_file, os_stat.st_uid, os_stat.st_gid)
    os.chmod(
        response_policy_file,
        stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP
    )  # 640


def whitelist():
    whitelist = set()

    whitelist_path = os.path.join(Path(home(), 'etc'))
    whitelist_file_prefix = CFG.get(CFG_GLOBAL, 'whitelist_file_prefix')

    for _, _, files in os.walk(whitelist_path):
        for each in files:
            if each.startswith(whitelist_file_prefix):
                with open(os.path.join(whitelist_path, each)) as file:
                    for line in file.readlines():
                        record = valid_record(line)
                        if record is not None:
                            whitelist.add(record)
    return whitelist


def write_file(content, path, write_mode):
    with open(path, write_mode) as file:
        file.write(content)
    return path


def zone_header():
    serial_db = os.path.join(Path(home()), 'var/db/serial.db')
    zone_header_db = os.path.join(Path(home()), 'var/db/zone_header.db')
    with open(zone_header_db, 'r') as file:
        header = file.read()
    return header.replace('*', zone_serial(serial_db))


def zone_serial(db):
    if not os.path.isfile(db):
        LOG.error('serial database missing, zone file not written')
        raise SystemExit(1)

    with open(db, 'r') as file:
        serial = file.read()

    next_serial = format_zone_serial(serial)

    with open(db, 'w+') as file:
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
        format = '%0' + str(len(index)) + 'g'
        next_index = format % (int(index) + 1)
        next_serial = today+next_index
    else:
        next_serial = str(int(serial) + 1)

    return next_serial


def skip_block_list_download():
    if CFG.get(CFG_GLOBAL, 'skip_block_list_download') == 'yes':
        return True
    return False


def run_dir():
    dir = CFG.get(CFG_GLOBAL, 'run_dir')

    if not dir:
        LOG.error('invalid run_dir: empty')
        raise SystemExit(1)

    if not dir.startswith('/'):
        LOG.error('invalid run_dir: must be an absolute path')
        raise SystemExit(1)

    return os.path.join(Path(dir), 'lists')


if __name__ == '__main__':
    raise SystemExit(main())
