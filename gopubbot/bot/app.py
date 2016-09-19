import logging
import os.path
import signal
import ssl

import simplejson as json
import tornado.httpserver
import tornado.ioloop
import tornado.web
from redis import Redis
from tornado import gen

from ..utils.crypto import get_random_string

from .api import BotApiClient


class WebHookHandler(tornado.web.RequestHandler):
    """Bot webhook handler."""

    def initialize(self, secret, update_handlers):
        self.secret = secret
        self.update_handlers = update_handlers

    @gen.coroutine
    def post(self, key):
        self.set_status(204)
        self.flush()
        if key == self.secret:
            update = json.loads(self.request.body)
            logging.info(update)
            for handler in self.update_handlers:
                yield handler.dispatch(update)


class BotApp(object):
    """The Bot himself."""

    def __init__(self, token, public_server_name, public_port=443, port=8000,
                 use_ssl=False, ssl_certfile=None, ssl_keyfile=None,
                 debug=False):
        self.debug = debug
        self.port = port
        self.ssl_certfile = ssl_certfile

        self.api = BotApiClient(token)
        self.update_handlers = []

        self.redis = Redis(decode_responses=True)

        webhook_secret = get_random_string(40)
        self.webhook_url = 'https://{}:{}/webhook/{}'.format(
            public_server_name, str(public_port), webhook_secret
        )

        app = tornado.web.Application([
            (
                r'/webhook/(?P<key>[^\/]+)', WebHookHandler,
                dict(secret=webhook_secret,
                     update_handlers=self.update_handlers)
            ),
        ], debug=self.debug)

        ssl_ctx = None
        if (use_ssl and ssl_certfile and ssl_keyfile):
            ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_ctx.load_cert_chain(os.path.abspath(ssl_certfile),
                                    os.path.abspath(ssl_keyfile))
        self.http_server = tornado.httpserver.HTTPServer(app,
                                                         ssl_options=ssl_ctx)

    def start(self):
        self.http_server.listen(self.port)

        def signal_handler(sig, frame):
            io_loop = tornado.ioloop.IOLoop.instance()
            io_loop.add_callback_from_signal(self.stop)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        self.register(self.webhook_url, self.ssl_certfile)

        tornado.ioloop.IOLoop.instance().start()

    @gen.coroutine
    def stop(self):
        self.http_server.stop()
        yield self.unregister()
        tornado.ioloop.IOLoop.instance().stop()

    @gen.coroutine
    def register(self, webhook_url, certificate=None):
        self.me = yield self.api.get_me()
        result = yield self.api.set_webhook(webhook_url, certificate)
        return result

    @gen.coroutine
    def unregister(self):
        result = yield self.api.set_webhook('')
        return result

    def add_update_handler(self, handler):
        self.update_handlers.append(handler(self.api, self.redis))
