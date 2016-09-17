import os.path
import ssl

import tornado.ioloop
import tornado.httpserver
import tornado.options
import tornado.web
from tornado.options import define, options

from .api_client import TelegramApiClient
from .urls import url_patterns


define('debug', type=bool, default=False, help='debug mode')
define('port', type=int, default=8000, help='run on the given port')
define('public_port', type=int, default=443, help='public server port')
define('public_server_name', type=str, help='public server name')
define('ssl', type=bool, default=False, help='use SSL')
define('ssl_certfile', type=str, help='path to SSL certificate file')
define('ssl_keyfile', type=str, help='path to SSL private key file')
define('telegram_api_token', type=str, help='Telegram bot API token')
define('config', type=str, default='/etc/gopubbot/config.py',
       help='tornado config file')

tornado.options.parse_command_line()

if os.path.isfile(options.config):
    tornado.options.parse_config_file(options.config)

api = TelegramApiClient(options.telegram_api_token)


def make_app(env='production'):
    """Make Tornado application."""
    print('https://' + options.public_server_name + ':' + str(options.public_port) + '/webhook/' + options.telegram_api_token)
    return tornado.web.Application(url_patterns, debug=options.debug)


def run():
    """Run server."""
    api.get_me()
    app = make_app()
    ssl_ctx = None
    if (options.ssl and options.ssl_certfile and options.ssl_keyfile):
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(os.path.abspath(options.ssl_certfile),
                                os.path.abspath(options.ssl_keyfile))
    http_server = tornado.httpserver.HTTPServer(app, ssl_options=ssl_ctx)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    run()
