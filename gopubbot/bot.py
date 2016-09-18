import os.path
import signal
import ssl

import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado import gen

from .api.client import BotApiClient
from .handlers import WebHookHandler


class Bot(object):
    """The Bot himself."""

    def __init__(self, token, public_server_name, public_port=443, port=8000,
                 use_ssl=False, ssl_certfile=None, ssl_keyfile=None,
                 debug=False):
        self.debug = debug
        self.port = port
        self.ssl_certfile = ssl_certfile

        self.api = BotApiClient(token)
        self.webhook_url = 'https://{}:{}/webhook/{}'.format(
            public_server_name, str(public_port), token
        )

        self.app = tornado.web.Application([
            (r'/webhook/(?P<token>[^\/]+)', WebHookHandler),
        ], debug=debug)

        ssl_ctx = None
        if (use_ssl and ssl_certfile and ssl_keyfile):
            ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_ctx.load_cert_chain(os.path.abspath(ssl_certfile),
                                    os.path.abspath(ssl_keyfile))
        self.http_server = tornado.httpserver.HTTPServer(self.app,
                                                         ssl_options=ssl_ctx)

    def start(self):
        self.http_server.listen(self.port)

        def _signal_handler(sig, frame):
            io_loop = tornado.ioloop.IOLoop.instance()
            io_loop.add_callback_from_signal(self.stop)

        signal.signal(signal.SIGTERM, _signal_handler)
        signal.signal(signal.SIGINT, _signal_handler)

        print(self.webhook_url)
        self.register(self.webhook_url, self.ssl_certfile)

        tornado.ioloop.IOLoop.instance().start()

    @gen.coroutine
    def stop(self):
        yield self.unregister()
        self.http_server.stop()
        tornado.ioloop.IOLoop.instance().stop()

    @gen.coroutine
    def register(self, webhook_url, certificate=None):
        self.me = yield self.api.get_me()
        print(self.me['username'])
        result = yield self.api.set_webhook(webhook_url, certificate)
        return result

    @gen.coroutine
    def unregister(self):
        result = yield self.api.set_webhook('')
        return result
