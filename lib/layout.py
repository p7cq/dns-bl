import os
import shutil
from pathlib import Path

from config import config
from config import own
from config import categories


def create_dir_layout(home_dir):
    sections = config().sections()
    separator = config().get(own(), 'section_separator')
    work_dir = os.path.join(Path(home_dir), config().get(own(), 'work_dir'))

    if os.path.exists(work_dir) and config().get(own(), 'remove_downloaded_content').lower() == 'yes':
        shutil.rmtree(work_dir)
        os.mkdir(work_dir)

    for section in sections:
        if section == own():
            continue

        block_categories = categories(section)

        if len(block_categories) > 0:
            for category in block_categories:
                provider = section.split(separator)[0]
                provider_dir = os.path.join(Path(work_dir), provider)
                category_dir = os.path.join(Path(provider_dir), category)

                if not os.path.exists(category_dir):
                    try:
                        os.makedirs(category_dir)
                    except FileExistsError:
                        pass
