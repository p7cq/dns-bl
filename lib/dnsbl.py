import os

from provider import get_block_lists
from policy import create_response_policy_file


def main():
    DNSBL_HOME = os.environ['DNSBL_HOME']

    get_block_lists(DNSBL_HOME)
    create_response_policy_file(DNSBL_HOME)


main()
