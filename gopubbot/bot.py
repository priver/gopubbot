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

from .api.client import BotApiClient
from .utils import get_random_string


class BotError(Exception):
    """Bot Error."""


class WebHookHandler(tornado.web.RequestHandler):
    """Bot webhook handler."""

    def initialize(self, secret, process_update):
        self.secret = secret
        self.process_update = process_update

    @gen.coroutine
    def post(self, key):
        self.set_status(204)
        if key == self.secret:
            yield self.process_update(json.loads(self.request.body))


class Bot(object):
    """The Bot himself."""

    def __init__(self, token, public_server_name, public_port=443, port=8000,
                 use_ssl=False, ssl_certfile=None, ssl_keyfile=None,
                 debug=False):
        self.debug = debug
        self.port = port
        self.ssl_certfile = ssl_certfile

        self.api = BotApiClient(token)
        self._update_handlers = {
            'message': [],
            'edited_message': [],
            'inline_query': [],
            'chosen_inlineesult': [],
            'callback_query': []
        }

        self._redis = Redis(decode_responses=True)

        webhook_secret = get_random_string(40)
        self.webhook_url = 'https://{}:{}/webhook/{}'.format(
            public_server_name, str(public_port), webhook_secret
        )

        app = tornado.web.Application([
            (
                r'/webhook/(?P<key>[^\/]+)', WebHookHandler,
                dict(secret=webhook_secret, process_update=self.process_update)
            ),
        ], debug=self.debug)

        ssl_ctx = None
        if (use_ssl and ssl_certfile and ssl_keyfile):
            ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_ctx.load_cert_chain(os.path.abspath(ssl_certfile),
                                    os.path.abspath(ssl_keyfile))
        self._http_server = tornado.httpserver.HTTPServer(app,
                                                          ssl_options=ssl_ctx)

    def start(self):
        self._http_server.listen(self.port)

        def _signal_handler(sig, frame):
            io_loop = tornado.ioloop.IOLoop.instance()
            io_loop.add_callback_from_signal(self.stop)

        signal.signal(signal.SIGTERM, _signal_handler)
        signal.signal(signal.SIGINT, _signal_handler)

        self.register(self.webhook_url, self.ssl_certfile)

        tornado.ioloop.IOLoop.instance().start()

    @gen.coroutine
    def stop(self):
        self._http_server.stop()
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

    def add_update_handler(self, update_types, handler):
        if isinstance(update_types, str):
            update_types = [update_types]

        for update_type in update_types:
            if update_type not in self._update_handlers.keys():
                raise BotError('Update type must be one of {}'.format(
                    ', '.join(self._update_handlers.keys())))

            self._update_handlers[update_type].append(handler)

    @gen.coroutine
    def process_update(self, update):
        logging.debug(update)
        for update_type in self._update_handlers.keys():
            if update_type in update:
                for handler in self._update_handlers[update_type]:
                    yield handler(update, self.api, self._redis)
                break
