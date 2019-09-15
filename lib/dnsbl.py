import os

from layout import create_dir_layout
from provider import get_blocklist
from policy import create_response_policy_file


def main():
    DNSBL_HOME = os.environ['DNSBL_HOME']

    create_dir_layout(DNSBL_HOME)
    get_blocklist(DNSBL_HOME)
    create_response_policy_file(DNSBL_HOME)


main()
