import os, re, sys, random, stat, tarfile, shutil, uuid

from configparser import ConfigParser
from pathlib import Path
from urllib.request import Request
from urllib.request import urlopen


def main():
    try:
        if len(DNSBL_HOME) == 0:
            raise NameError('DNSBL_HOME environment variable not found')
        init()
        get_block_lists()
        create_response_policy_file()
    except Exception as e:
        handle_error(e)


def get_block_lists():
    if debug():
        return # also, do not download new files (and keep existing ones)

    if os.path.exists(CFG_WORK_DIR):
        shutil.rmtree(CFG_WORK_DIR)
        os.mkdir(CFG_WORK_DIR)

    for section in CFG.sections():
        if section == CFG_GLOBAL:
            continue

        if CFG.get(section, 'enabled').lower() == 'yes':
            url = CFG.get(section, 'url')
            provider = re.sub('[^A-Za-z0-9._-]', '_', section) # replace other (filename unfriendly) characters with underscore
            provider_dir = os.path.join(CFG_WORK_DIR, provider)
            tmp_file_path = os.path.join(provider_dir, str(uuid.uuid4())) # and make sure we do not overwrite stuff
            create_dir(provider_dir)
            try:
                download(url, tmp_file_path)
                normalize_source(tmp_file_path, section, provider_dir)
            except Exception as e:
                handle_error(e, 'exception caught while processing [' +section+ '] at ' +url)


def normalize_source(tmp_file_path, section, provider_dir):
    file_type = CFG.get(section, 'file_type')
    categories = CFG.get(section, 'categories').split(',')
    if file_type == 'gzip':
        top_dir_name = 'BL' # directory under which categories are extracted from shallalist.tar.gz
        tar = tarfile.open(tmp_file_path, 'r:gz')

        for member in tar.getmembers():
            for category in categories:
                category_path_in_tar = os.path.join(Path(top_dir_name), category, CFG_BLOCKFILE_NAME)
                member_name = member.name
                if member_name == category_path_in_tar:
                    uid = str(uuid.uuid4())
                    create_dir(os.path.join(Path(provider_dir, uid)))
                    write_file(tar.extractfile(member_name).read(), os.path.join(Path(provider_dir, uid, CFG_BLOCKFILE_NAME)), 'wb')

        os.remove(tmp_file_path)

    if file_type == 'text':
        for category in categories:
            uid = str(uuid.uuid4())
            create_dir(os.path.join(Path(provider_dir, uid)))
            os.rename(tmp_file_path, os.path.join(provider_dir, uid, CFG_BLOCKFILE_NAME))


def create_response_policy_file():
    domains = filter_domains()
    if len(domains) > 0:
        response_policy_file = CFG.get(CFG_GLOBAL, 'rpz_file')

        if os.path.isfile(response_policy_file):
            os.remove(response_policy_file) # remove existing RPZ file
        try:
            file = open(response_policy_file, 'a')
            file.write(get_zone_header().strip() + '\n')
            for domain in domains:
                record = domain + '\n'
                subdomain_record = ''
                if CFG.get(CFG_GLOBAL, 'add_subdomains').lower() == 'yes':
                    subdomain_record = '*.' + record
                file.write(record + subdomain_record)
            change_permissions(response_policy_file)
        finally:
            file.close()
    else:
        handle_error('no sections available, nothing to do')


def filter_domains():
    redirect = CFG.get(CFG_GLOBAL, 'redirect')
    whitelist = get_whitelist()
    domains = set()

    for r, d, files in os.walk(CFG_WORK_DIR):
        for f in files:
            if f == CFG_BLOCKFILE_NAME:
                try:
                    file = open(os.path.join(r, f), 'r')
                    try:
                        lines = file.readlines()
                    except UnicodeDecodeError:# bypass some weird characters in source
                        pass
                finally:
                    file.close()
                for line in lines:
                    entry = sanitize(line)
                    if not valid(entry):
                        continue
                    if entry in whitelist:
                        continue
                    domains.add(entry + ' ' + redirect)
    print(len(domains)) # not counting subdomains
    return domains


def valid(record): # any record that makes it to RPZ file is validated here
    if '#' in record:
        return False
    if is_ipv4(record):
        return False
    if ' ' in record and '\t' in record or '\n' in record or '\r' in record or '\v' in record or '\f' in record:
        return False
    if record.endswith('.'):
        return False
    if '/' in record:
        return False
    if '&' in record:
        return False
    if '.' not in record:
        return False
    if record.startswith('-'):
        return False
    return True


def sanitize(line):
    line = line.strip()
    line = line.replace('\t', ' ')
    if line.startswith('0.0.0.0 ') or line.startswith('127.0.0.1 '):
        line = line.split()[1]
    return line


def change_permissions(response_policy_file): # change RPZ file permissions to parent directory's owner and group
    response_policy_dir_path = Path(response_policy_file)
    os_stat = os.stat(response_policy_dir_path.parent.absolute())
    os.chown(response_policy_file, os_stat.st_uid, os_stat.st_gid)
    os.chmod(response_policy_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP) # 640


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
    request = Request(url, headers={'User-Agent': user_agent()}) # use a browser user agent as some sites block urllib's ua
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
        'Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.166 Safari/537.36'
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


def get_zone_header():
    serial_db = os.path.join(Path(DNSBL_HOME), 'var/db/serial.db')
    zone_header_db = os.path.join(Path(DNSBL_HOME), 'var/db/zone_header.db')
    with open(zone_header_db, 'r') as file:
        header = file.read()
    return header.replace('*', get_zone_sn(serial_db))


def get_zone_sn(db): # read last used serial from db
    if not os.path.isfile(db):
        raise RuntimeError('serial database missing, zone file not written')
    with open(db, 'r') as file:
        serial = file.read()

    if not serial:
        raise RuntimeError('empty serial database, zone file not written')

    serial_current = str(int(serial) + 1)

    with open(db, 'w+') as file:
        file.write(serial_current)
    return serial_current


def get_whitelist():
    whitelist_path = os.path.join(Path(DNSBL_HOME, 'conf'))
    whitelist_file_prefix = CFG.get(CFG_GLOBAL, 'whitelist_file_prefix')
    whitelist = set()
    for r, d, files in os.walk(whitelist_path):
        for f in files:
            if f.startswith(whitelist_file_prefix):
                try:
                    file = open(os.path.join(whitelist_path, f))
                    lines = file.readlines()
                finally:
                    file.close()
                for line in lines:
                    whitelist.add(line.strip())
    return whitelist


def handle_error(e, message = ''):
    if not debug():
        if len(message) > 0:
            print("{}\n{}: {}".format(message, type(e).__name__, e))
        else:
            print("{}".format(e))
    else:
        raise


def init():
    try:
        CFG.read_file(open(CFG_INI_FILE))
    except Exception as e:
        handle_error("no configuration file was found \
            \na default configuration will be generated at " +CFG_INI_FILE+ "\n")
        cfg_default()
    CFG.read(CFG_INI_FILE, 'utf8')


def cfg_default():
    CFG['global'] = {
        'rpz_file': os.path.join(DNSBL_HOME, 'rpz.db'),
        'redirect': 'IN CNAME .',
        'add_subdomains': 'no',
        'whitelist_file_prefix': 'whitelist_'
    }

    create_dir(str(Path(CFG_INI_FILE).parent.absolute()))
    with open(CFG_INI_FILE, 'w') as file:
        CFG.write(file)


def debug():
    return False


DNSBL_HOME = os.environ['DNSBL_HOME']
CFG = ConfigParser()
CFG_INI_FILE = os.path.join(Path(DNSBL_HOME), 'conf/dns-bl.ini')
CFG_WORK_DIR = os.path.join(Path(DNSBL_HOME), 'var/run/bl')
CFG_GLOBAL = 'global' # global section
CFG_BLOCKFILE_NAME = 'domains' # name of the file in downloaded content


main()
