import time
import json
import os.path
import re
import sys
import mimetypes
import ssl
from datetime import datetime

import asyncio
import aiohttp_jinja2
import jinja2
from aiohttp import web

import aioipfs

import ipfsgwx
from ipfsgwx import webrunner


def human_datetime(t):
    return datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')


def join(*pieces):
    return '/'.join(p.strip() for p in pieces).replace('//', '/')


def debug(msg):
    print('{0}: {1}'.format(human_datetime(time.time()), msg), file=sys.stderr)


def time_now():
    return int(time.time())


def error(msg='Unspecified error', status=500):
    return web.Response(text=msg, status=status)


def resolve_error():
    return error(msg='Resolve error')


def notfound(msg='Not found', status=404):
    return web.Response(text=msg, status=status)


def parse_config(path):
    try:
        config = json.loads(open(path, 'rt').read())
    except Exception as e:
        print('Invalid config: {}'.format(str(e)), file=sys.stderr)
        return None

    return config


def build_response(data, filename):
    response = web.Response(status=200)
    response.content_type = 'application/octet-stream'
    mtype = mimetypes.guess_type(filename)
    if mtype[0]:
        response.content_type = mtype[0]
    response.body = data
    return response


async def directory_listing(request, client, path):
    ctx = {}
    try:
        listing = await client.core.ls(path)
    except aioipfs.APIError:
        return notfound()

    if 'Objects' not in listing:
        return notfound()

    ctx['path'] = request.path
    ctx['links'] = []

    for obj in listing['Objects']:
        if 'Hash' not in obj:
            continue
        if obj['Hash'] == path:
            ctx['links'] += obj.get('Links', [])

    for lnk in ctx['links']:
        lnk['href'] = join(request.path, lnk['Name'])

    response = aiohttp_jinja2.render_template('ipfsdirlisting.html',
                                              request,
                                              ctx)
    return response


async def render_directory(request, client, path):
    index_path = join(path, 'index.html')

    try:
        data = await client.cat(index_path)
    except aioipfs.APIError as exc:
        if exc.code == 0 and exc.message.startswith('no link named'):
            return await directory_listing(request, client, path)
        if exc.code == 0 and exc.message == 'this dag node is a directory':
            return await directory_listing(request, client, path)
    else:
        basename = os.path.basename(index_path)
        return build_response(data, basename)


async def render_path(request, client, path):
    try:
        data = await client.cat(path)
    except aioipfs.APIError as exc:
        if exc.code == 0 and exc.message.startswith('no link named'):
            return notfound()
        if exc.code == 0 and exc.message == 'this dag node is a directory':
            return await render_directory(request, client, path)
    else:
        basename = os.path.basename(path)
        return build_response(data, basename)


async def vhost_sink_handler(request):
    ipns_cache = request.app.ipns_cache
    ipfs_client = request.app.ipfs_client
    config = request.app.config
    vhosts = config.get('vhosts', None)

    host_header = request.headers.get('Host', None)

    if not host_header:
        return error('No host header')

    vhost_matched = None
    for vhost_re in vhosts.keys():
        ma = re.search(vhost_re, host_header, re.IGNORECASE)
        if ma:
            vhost_matched = vhosts[vhost_re]
            break

    if not vhosts or not vhost_matched:
        return error('Unknown host')

    ipfs_path = None
    vhost = vhost_matched
    vhost_ipns_key = vhost.get('ipns', None)
    vhost_ipfs_hash = vhost.get('ipfs', None)

    async with ipfs_client as client:
        if vhost_ipns_key and vhost_ipfs_hash is None:
            cached = ipns_cache.get(vhost_ipns_key, None)
            if not cached:
                return resolve_error()

            ipfs_path = cached.get('path', None)
            if not ipfs_path:
                return resolve_error()
        elif vhost_ipfs_hash:
            if not vhost_ipfs_hash.startswith('/ipfs'):
                ipfs_path = os.path.join('/ipfs', vhost_ipfs_hash)
            else:
                ipfs_path = vhost_ipfs_hash

        path = join(ipfs_path, request.path_qs)
        return await render_path(request, client, path)

    return error(msg='Not found')


async def ipns_cache_task(args, app, config, sleeptime=10):
    default_cache_ttl = 60 * 10
    client = app.ipfs_client
    last_saved = None

    while True:
        was_updated = False  # an entry in the cache was changed

        vhosts = config.get('vhosts', {})
        now = time_now()

        for vhost_re, vhost in vhosts.items():
            ipns_key = vhost.get('ipns', None)
            if not ipns_key:
                # No IPNS key, nothing to resolve
                continue
            try:
                ipns_ttl = int(vhost.get('cachettl', default_cache_ttl))
            except BaseException:
                ipns_ttl = default_cache_ttl

            cached = app.ipns_cache.get(ipns_key, None)

            if cached is not None and (now - cached['last']) < ipns_ttl:
                # We have an acceptable entry in the cache, don't update yet
                continue

            try:
                resolved = await client.name.resolve(ipns_key)
            except aioipfs.APIError as exc:
                # Problem when resolving the IPNS key
                if args.debug:
                    debug('IPNS: resolve error for {0}: {1}'.format(
                        ipns_key, exc.message))
                continue

            if 'Path' not in resolved:
                continue

            # Should we check for 'Path' to be properly formatted?
            resolved_path = resolved['Path']

            # Add the record in the cache
            app.ipns_cache[ipns_key] = {
                'path': resolved_path,
                'last': time_now(),
            }
            was_updated = True

            if args.debug:
                debug('IPNS: updated vhost {0}, IPFS path is: {1}'.format(
                    vhost_re, resolved_path))

        if not last_saved or was_updated:
            async with app.lock:
                with open(app.ipnscache_path, "w+t") as fd:
                    json.dump(app.ipns_cache, fd)
                last_saved = now
                if args.debug:
                    debug('IPNS: saved cache')

        await asyncio.sleep(sleeptime)


async def app_stop(app):
    app.ipns_cache_task.cancel()
    if app.ipfs_client:
        await app.ipfs_client.close()


def setup_app(args):
    ipfs_client = aioipfs.AsyncIPFS(host=args.ipfsapihost,
                                    port=args.ipfsapiport)

    if not args.config or not os.path.isfile(args.config):
        sys.exit('Config file {} does not exist'.format(args.config))

    config = parse_config(args.config)

    if config is None:
        sys.exit('Invalid config file, check its syntax')

    loop = asyncio.get_event_loop()
    app = web.Application()
    app.ipnscache_path = config.get(
        'ipnscachepath', os.path.join(
            os.getcwd(), 'ipnscache.json'))
    app.lock = asyncio.Lock()
    app.ipfs_client = ipfs_client
    app.config = config

    try:
        app.ipns_cache = json.load(open(app.ipnscache_path, 'rt'))
        if args.debug:
            debug('Loaded IPNS cache: {} record(s)'.format(
                len(app.ipns_cache.keys())))
    except BaseException:
        app.ipns_cache = {}

    app.ipns_cache_task = loop.create_task(ipns_cache_task(args, app, config))

    templates_path = os.path.join(os.path.dirname(ipfsgwx.__file__),
                                  'templates')
    aiohttp_jinja2.setup(app,
                         loader=jinja2.FileSystemLoader(templates_path))

    app.router.add_get('/{name:.*}', vhost_sink_handler)

    return setup_app_sites(args, app, config)


def setup_app_sites(args, app, config):
    config_listen = config.get('listen', {})
    app_runner = webrunner.get_app_runner(app)

    all_sites = []

    # Parse the 'listen' section and the config and configure the sites
    for listen_addrspec, listen_params in config_listen.items():
        # Regexps for matching the listen addresses
        addr_regexps = [
            r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):([0-9]+)',  # ipv4
            r'\[([:*a-f0-9]+){0,12}\]:([0-9]+)'  # ipv6
        ]
        listen_addr, listen_port = None, 0
        for regexp in addr_regexps:
            match = re.search(regexp, listen_addrspec)
            if match:
                listen_addr = match.group(1)
                listen_port = match.group(2)
                break

        if not listen_addr or not listen_port:
            continue

        listen_proto = listen_params.get('proto', 'http')
        runner_site_params = {
            'host': listen_addr,
            'ports': [listen_port],
        }

        if listen_proto == 'http':
            all_sites += webrunner.config_site(app_runner,
                                               **runner_site_params)
        if listen_proto == 'https':
            # Create SSL context
            cert = listen_params.get('certificate', None)
            key = listen_params.get('key', None)

            if not cert or not key:
                if args.debug:
                    debug('config: Invalid SSL cert/key config for {}'.format(
                        listen_addr))
                continue
            try:
                context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
                context.load_cert_chain(certfile=cert, keyfile=key)
            except Exception:
                if args.debug:
                    debug('config: Could not load SSL context for {}'.format(
                        listen_addr))
                continue

            runner_site_params['ssl_context'] = context
            all_sites += webrunner.config_site(app_runner,
                                               **runner_site_params)

    return webrunner.run_sites(app, runner=app_runner, sites=all_sites,
                               onexit=app_stop, print=debug)
