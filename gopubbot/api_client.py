import tornado.httpclient
import simplejson as json


class TelegramApiClient(object):
    """Telegram bot API client."""

    def __init__(self, token):
        self.http_client = tornado.httpclient.AsyncHTTPClient()
        self.api_url = 'https://api.telegram.org/bot{token}/{{method}}'.format(
            token=token
        )

    def _handle_response(self, response):
        if response.error:
            print('Error: ', response.error)
        else:
            try:
                print(json.loads(response.body)['result'])
            except json.JSONDecodeError as e:
                print('Error: ', e.message)

    def _fetch(self, method):
        self.http_client.fetch(self.api_url.format(method=method),
                               self._handle_response)

    def get_me(self):
        self._fetch('getMe')
