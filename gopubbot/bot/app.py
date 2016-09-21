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

from .update import UpdateDispatcher, UpdateHandlerSpec
from .api import BotApiClient


class WebHookHandler(tornado.web.RequestHandler):
    """Webhook updates handler."""

    def initialize(self, secret, dispatcher):
        self.secret = secret
        self.dispatcher = dispatcher

    @gen.coroutine
    def post(self, key):
        self.set_status(204)
        self.flush()
        if key == self.secret:
            update = json.loads(self.request.body)
            logging.info(update)
            yield self.dispatcher.dispatch(update)


class BotApp(object):
    """Bot tornado web application."""

    def __init__(self, update_handlers, token, public_server_name,
                 public_port=443, port=8000, use_ssl=False, ssl_certfile=None,
                 ssl_keyfile=None, debug=False):
        self.debug = debug
        self.port = port
        self.ssl_certfile = ssl_certfile

        self.api = BotApiClient(token)
        self.redis = Redis(decode_responses=True)

        self.update_handlers = {}
        for update_type, update_type_handlers in update_handlers.items():
            self.update_handlers[update_type] = []
            for spec in update_type_handlers:
                if not isinstance(spec, UpdateHandlerSpec):
                    spec = UpdateHandlerSpec(spec)
                spec.init_handler(self.api, self.redis)
                self.update_handlers[update_type].append(spec)
        self.dispatcher = UpdateDispatcher(self.update_handlers)

        webhook_secret = get_random_string(40)
        self.webhook_url = 'https://{}:{}/webhook/{}'.format(
            public_server_name, str(public_port), webhook_secret
        )

        app = tornado.web.Application([
            (r'/webhook/(?P<key>[^\/]+)', WebHookHandler,
             dict(secret=webhook_secret, dispatcher=self.dispatcher)),
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
