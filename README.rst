========
ipfs-gwx
========

Simple IPFS <=> HTTP gw with virtual hosts support to serve content locally to
your network.

It uses Python 3.5 and is built around the aiohttp_ asynchronous HTTP framework.  

Installation
============

PIP
---

Assuming you have Python 3.5 installed:

.. code-block:: shell

    pip install -r requirements.txt
    python setup.py install

Docker
------

A Dockerfile is provided. By default the container assumes you have a
**go-ipfs** container reachable via the hostname **ipfs**, so just run a
**ipfs/go-ipfs** container, then fire the **ipfs-gwx** container and link them:

.. code-block:: shell

    docker pull ipfs/go-ipfs:latest
    docker build -t ipfs-gwx .
    docker run --name ipfs1 ipfs/go-ipfs
    docker run -it --link ipfs1:ipfs ipfs-gwx

Usage
=====

.. code-block:: shell

    ipfs-gwx --config ipfs-gwx.conf

Use **-d** to enable debug.

IPFS daemon configuration
-------------------------

By default it will connect to **localhost**, port **5001**.

Use **--ipfsapihost** and **--ipfsapiport** to specify which IPFS daemon to
connect to, e.g:

.. code-block:: shell

    ipfs-gwx --config ipfs-gwx.conf --ipfsapihost 192.168.1.1 --ipfsapiport 5004

Configuration
=============

Configuration is done via a simple JSON file, look in the **examples**
directory for simple examples. A configuration for relaying
**/ipns/ipfs.io** on port 80 would be:

.. code-block:: json

    {
        "ipnscachepath": "/tmp/ipfsgwx-cache.json",
        "listen": {
            "0.0.0.0:80": {
                "proto": "http"
            }
        },
        "vhosts": {
            ".*": {
                "ipns": "ipfs.io"
            }
        }
    }

HTTPS is supported:

.. code-block:: json

    "listen": {
        "0.0.0.0:443": {
            "proto": "https",
            "certificate": "/path/to/cert.pem",
            "key": "/path/to/cert.key"
        }
    }

Virtual hosts
-------------

Virtual hosts support proxying from the IPNS or IPFS namespace. Define your 
virtual hosts in the **vhosts** section. The virtual host key is a Python
regular expression that is matched against the HTTP **Host:** header. You can
use a **get-all** wildcard but always put it last:

.. code-block:: json

    "vhosts": {
        "my-website.example.com": {
            "ipns": "mykey"
        },
        ".*": {
            // default vhost if no match
        }
    }

Proxying IPFS hashes
^^^^^^^^^^^^^^^^^^^^

To serve **/ipfs/QmYNQJoKGNHTpPxCBPh9KkDpaExgd2duMa3aF6ytMpHdao** on
**localhost** for example, use:

.. code-block:: json

    "vhosts": {
        "localhost": {
            "ipfs": "/ipfs/QmYNQJoKGNHTpPxCBPh9KkDpaExgd2duMa3aF6ytMpHdao"
        }
    }

or without the **/ipfs** prefix:

.. code-block:: json

    "vhosts": {
        "localhost": {
            "ipfs": "QmYNQJoKGNHTpPxCBPh9KkDpaExgd2duMa3aF6ytMpHdao"
        }
    }

Proxying IPNS hashes/names
^^^^^^^^^^^^^^^^^^^^^^^^^^

The default TTL for entries in the IPNS cache is **10 minutes** but you should
always override it using the **cachettl** (time in seconds) key in the virtual
host config:

.. code-block:: json

    "vhosts": {
        "localhost": {
            "ipns": "ipfs.io",
            "cachettl": "3600"
        }
    }

Features
========

- Virtual hosts
- Configurable IPNS cache when needed
- HTTPS and IPv6 support
- Directory listing (similar to go-ipfs_'s gateway, thanks to dir-index-html_)

.. _dir-index-html: https://github.com/ipfs/dir-index-html
.. _go-ipfs: https://github.com/ipfs/go-ipfs

Requirements
============

- Python >= 3.5
- aioipfs_
- aiohttp_

.. _aiohttp: https://pypi.python.org/pypi/aiohttp
.. _aioipfs: https://gitlab.com/cipres/aioipfs

Thanks
======

Many thanks to the IPFS community for this great project.

License
=======

**ipfs-gwx** is offered under the GNU GPL3 license.
