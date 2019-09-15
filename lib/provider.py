import os
import tarfile
import uuid
from pathlib import Path

from config import config
from config import own
from config import categories
from common import download
from common import write_file


def get_blocklist(home_dir):
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
            save_path = os.path.join(provider_dir, str(uuid.uuid4()))
            extract_and_transform(download(url, save_path), section, provider_dir)


def extract_and_transform(save_path, section, provider_dir):
    
    top_dir_name = config().get(section, 'top_dir_name')
    block_file_name = config().get(own(), 'block_file_name')
    mime_type = config().get(section, 'mime_type')
    
    if mime_type == 'application/gzip':
        tar = tarfile.open(save_path, 'r:gz')

        for member in tar.getmembers():
            for category in categories(section):
                category_path_in_tar = os.path.join(Path(top_dir_name), category, block_file_name)
                member_name = member.name

                if member_name == category_path_in_tar:
                    write_file(tar.extractfile(member_name).read(),
                               os.path.join(Path(provider_dir, category, block_file_name)), 'wb')
        os.remove(save_path)

    if mime_type == 'text/plain':
        os.rename(save_path, os.path.join(provider_dir, top_dir_name, block_file_name))
