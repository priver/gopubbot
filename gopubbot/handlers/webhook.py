import simplejson as json
import tornado.web
from tornado.options import options


class WebHookHandler(tornado.web.RequestHandler):
    """Telegram bot API webhook handler."""

    def post(self, token):
        if token == options.telegram_api_token:
            try:
                print(json.loads(self.request.body))
            except json.JSONDecodeError:
                pass
        self.set_status(204)
