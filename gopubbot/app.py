import os.path

import tornado.options
from tornado.options import define, options

from .bot import Bot

define('debug', type=bool, default=False, help='debug mode')
define('port', type=int, default=8000, help='run on the given port')
define('public_port', type=int, default=443, help='public server port')
define('public_server_name', type=str, help='public server name')
define('use_ssl', type=bool, default=False, help='use SSL')
define('ssl_certfile', type=str, help='path to SSL certificate file')
define('ssl_keyfile', type=str, help='path to SSL private key file')
define('bot_api_token', type=str, help='Telegram bot API token')
define('config', type=str, default='/etc/gopubbot/config.py',
       help='tornado config file')

tornado.options.parse_command_line()

if os.path.isfile(options.config):
    tornado.options.parse_config_file(options.config)


def run():
    """Start bot server."""
    bot = Bot(
        token=options.bot_api_token,
        public_server_name=options.public_server_name,
        public_port=options.public_port,
        port=options.port,
        use_ssl=options.use_ssl,
        ssl_certfile=options.ssl_certfile,
        ssl_keyfile=options.ssl_keyfile,
        debug=options.debug,
    )
    bot.start()

if __name__ == '__main__':
    run()
