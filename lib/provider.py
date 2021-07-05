import os
import tarfile
import shutil
import uuid
from pathlib import Path

from config import config
from config import own
from config import categories
from common import download
from common import write_file
from common import create_dir


def get_block_lists(home_dir):
    create_dir_layout(home_dir)

    if config().get(own(), 'download_enabled').lower() != 'yes':
        return

    work_dir = os.path.join(Path(home_dir), config().get(own(), 'work_dir'))
    sections = config().sections()
    separator = config().get(own(), 'section_separator')

    for section in sections:
        if section == own():
            continue

        if config().get(section, 'enabled').lower() == 'yes':
            url = config().get(section, 'url')
            provider = section.split(separator)[0]
            provider_dir = os.path.join(Path(work_dir), provider)
            tmp_file_path = os.path.join(provider_dir, str(uuid.uuid4())) # temp download path
            normalize_sources(download(url, tmp_file_path), section, provider_dir)


def create_dir_layout(home_dir):
    sections = config().sections()
    separator = config().get(own(), 'section_separator')
    work_dir = os.path.join(Path(home_dir), config().get(own(), 'work_dir'))

    if os.path.exists(work_dir) and config().get(own(), 'remove_downloaded_content').lower() == 'yes':
        shutil.rmtree(work_dir)
        os.mkdir(work_dir)

    for section in sections:
        if section == own() or config().get(section, 'enabled').lower() == 'no':
            continue

        block_categories = categories(section)

        if len(block_categories) > 0:
            for category in block_categories:
                provider = section.split(separator)[0]
                create_dir(os.path.join(Path(work_dir), provider))


def normalize_sources(tmp_file_path, section, provider_dir):
    block_file_name = config().get(own(), 'block_file_name')
    mime_type = config().get(section, 'mime_type')

    if mime_type == 'application/gzip':
        top_dir_name = 'BL' # directory under all categories are extracted from shallalist.tar.gz
        tar = tarfile.open(tmp_file_path, 'r:gz')

        for member in tar.getmembers():
            for category in categories(section):
                category_path_in_tar = os.path.join(Path(top_dir_name), category, block_file_name)
                member_name = member.name
                if member_name == category_path_in_tar:
                    uid = str(uuid.uuid4())
                    create_dir(os.path.join(Path(provider_dir, uid)))
                    write_file(tar.extractfile(member_name).read(), os.path.join(Path(provider_dir, uid, block_file_name)), 'wb')

        os.remove(tmp_file_path)

    if mime_type == 'text/plain':
        for category in categories(section):
            uid = str(uuid.uuid4())
            create_dir(os.path.join(Path(provider_dir, uid)))
            os.rename(tmp_file_path, os.path.join(provider_dir, uid, block_file_name))

