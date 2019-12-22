import asyncio

from aiohttp.log import access_logger
from aiohttp.web_exceptions import *  # noqa
from aiohttp.web_fileresponse import *  # noqa
from aiohttp.web_middlewares import *  # noqa
from aiohttp.web_protocol import *  # noqa
from aiohttp.web_request import *  # noqa
from aiohttp.web_response import *  # noqa
from aiohttp.web_server import *  # noqa
from aiohttp.web_runner import AppRunner, GracefulExit, TCPSite


def get_app_runner(app, access_log=access_logger):
    loop = asyncio.get_event_loop()
    runner = AppRunner(app, handle_signals=True,
                       access_log=access_log)
    loop.run_until_complete(runner.setup())
    return runner


def config_site(runner, host='0.0.0.0', ports=[],
                shutdown_timeout=60.0, ssl_context=None,
                backlog=128,
                access_log=access_logger, handle_signals=True,
                reuse_address=None, reuse_port=None):
    sites = []
    for port in ports:
        sites.append(TCPSite(runner, host, port,
                             shutdown_timeout=shutdown_timeout,
                             ssl_context=ssl_context,
                             backlog=backlog,
                             reuse_address=reuse_address,
                             reuse_port=reuse_port))
    return sites


def run_sites(app, *, sites=[], runner=None, onexit=None, print=print):
    loop = asyncio.get_event_loop()

    if not runner:
        raise Exception('Where the runner at, slug ?')

    try:
        for site in sites:
            loop.run_until_complete(site.start())
        try:
            for s in runner.sites:
                print('Listening on {}'.format(s.name))
            loop.run_forever()
        except (GracefulExit, KeyboardInterrupt):
            pass
    finally:
        loop.run_until_complete(runner.cleanup())
    if hasattr(loop, 'shutdown_asyncgens'):
        loop.run_until_complete(loop.shutdown_asyncgens())
    if onexit:
        loop.run_until_complete(onexit(app))
    loop.close()
