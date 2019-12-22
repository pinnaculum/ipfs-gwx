
import os
import os.path
import re
import sys
import codecs
from setuptools import setup

PY_VER = sys.version_info

if PY_VER >= (3, 5):
    pass
else:
    raise RuntimeError("You need python3.5 or newer")

with codecs.open(os.path.join(os.path.abspath(os.path.dirname(
        __file__)), 'ipfsgwx', '__init__.py'), 'r', 'latin1') as fp:
    try:
        version = re.findall(r"^__version__ = '([^']+)'\r?$",
                             fp.read(), re.M)[0]
    except IndexError:
        raise RuntimeError('Unable to determine version.')

setup(
    name='ipfs-gwx',
    version=version,
    license='GPL3',
    author='David Ferlier',
    url='https://github.com/pinnaculum/ipfs-gwx',
    description='Async HTTP/HTTPS proxy for IPFS',
    packages=['ipfsgwx'],
    include_package_data=False,
    install_requires=[
        'aiohttp',
        'aioipfs',
        'aiohttp-jinja2'
    ],
    entry_points={
        'console_scripts': [
            'ipfs-gwx = ipfsgwx:run',
        ]
    },
    classifiers=[
        'Framework :: AsyncIO',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
        'Programming Language :: Python',
        'Intended Audience :: Developers',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: GNU Affero General Public License v3',
    ],
    keywords=[
        'async',
        'io',
        'aiohttp',
        'ipfs'
    ],
)
