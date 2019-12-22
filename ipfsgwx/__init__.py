
__version__ = '0.1.0'

import argparse

from ipfsgwx import core


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ipfsapihost', default='localhost', metavar='str',
                        help='IPFS daemon hostname')
    parser.add_argument('--ipfsapiport', default=5001, metavar='str',
                        help='IPFS daemon port')
    parser.add_argument('--config', default='./ipfs-gwx.conf', metavar='str',
                        help='Config path')
    parser.add_argument('-d', action='store_true',
                        dest='debug', help='Activate debugging')
    args = parser.parse_args()

    core.setup_app(args)
