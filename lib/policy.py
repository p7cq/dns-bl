import os
from pathlib import Path

from config import config
from config import own
from config import categories
from db import get_serial
from db import get_zone_header
from common import is_ipv4


# response policy zone file creation

def whitelisted_domains(home_dir):
    whitelist_path = os.path.join(Path(home_dir, 'var/db'))
    whitelist_file_prefix = config().get(own(), 'whitelist_file_prefix')
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


def header(home_dir):
    serial_db = os.path.join(Path(home_dir), 'var/db/serial.db')
    zone_header_db = os.path.join(Path(home_dir), 'var/db/zone_header.db')
    return get_zone_header(zone_header_db).replace('*', get_serial(serial_db))


# any record that makes it to RPZ file is validated here
def valid(record):
    if is_ipv4(record):
        return False
    if ' ' in record or '\t' in record or '\n' in record or '\r' in record or '\v' in record or '\f' in record:
        return False
    if record.endswith('.'):
        return False
    if '/' in record:
        return False
    if '&' in record:
        return False
    if '#' in record:
        return False
    if '.' not in record:
        return False
    if record.startswith('-'):
        return False
    return True


def filter_domains(home_dir):
    work_dir = os.path.join(Path(home_dir), config().get(own(), 'work_dir'))
    block_file_name = config().get(own(), 'block_file_name')
    redirect = config().get(own(), 'redirect')
    whitelist = whitelisted_domains(home_dir)
    domains = set()
    for r, d, files in os.walk(work_dir):
        for f in files:
            if f == block_file_name:
                try:
                    file = open(os.path.join(r, f), 'r')
                    try:
                        lines = file.readlines()
                    except UnicodeDecodeError:# bypass some weird characters in source
                        pass
                finally:
                    file.close()
                for line in lines:
                    domain = line.strip()
                    if not valid(domain):
                        continue
                    if domain in whitelist:
                        continue
                    domains.add(domain + ' ' + redirect)
    print(len(domains))
    return domains


def create_response_policy_file(home_dir):
    domains = filter_domains(home_dir)
    if len(domains) > 0:
        # remove existing file
        response_policy_file = config().get(own(), 'rpz_file')
        if os.path.isfile(response_policy_file):
            os.remove(response_policy_file)
        add_subdomains = config().get(own(), 'add_subdomains')
        try:
            file = open(response_policy_file, 'a')
            file.write(header(home_dir).strip() + '\n')
            for domain in domains:
                record = domain + '\n'
                subdomain_record = ''
                if add_subdomains.lower() == 'yes':
                    subdomain_record = '*.' + record
                file.write(record + subdomain_record)
        finally:
            file.close()
