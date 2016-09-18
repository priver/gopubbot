import simplejson as json
import tornado.web
from tornado.options import options


class WebHookHandler(tornado.web.RequestHandler):
    """Bot API webhook handler."""

    def post(self, token):
        if token == options.bot_api_token:
            try:
                print(json.loads(self.request.body))
            except json.JSONDecodeError:
                pass
        self.set_status(204)
