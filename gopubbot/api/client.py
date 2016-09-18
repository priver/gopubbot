import urllib.parse

import simplejson as json
from tornado import gen
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.httputil import HTTPHeaders

from .multipart import encode_multipart_formdata


class BotApiError(Exception):
    """Bot API Error."""


class BotApiClient(object):
    """Bot API client."""

    def __init__(self, token):
        self._http_client = AsyncHTTPClient(force_instance=True)
        self._api_url = 'https://api.telegram.org/bot{token}/{{method}}'.format(
            token=token
        )

    def _parse_response(self, response):
        data = json.loads(response.body)
        print(data)
        if not data['ok']:
            raise BotApiError(data['description'])
        return data['result']

    @gen.coroutine
    def _fetch(self, method, params=None, files=None):
        url = self._api_url.format(method=method)
        http_method = 'GET'
        headers = HTTPHeaders()
        body = None

        if files is not None:
            http_method = 'POST'
            body, content_type = encode_multipart_formdata(params, files)
            headers.add('Content-Type', content_type)
        elif params is not None:
            http_method = 'POST'
            body = urllib.parse.urlencode(params)

        request = HTTPRequest(url, method=http_method,
                              headers=headers, body=body)
        response = yield self._http_client.fetch(request)
        return self._parse_response(response)

    @gen.coroutine
    def get_me(self):
        result = yield self._fetch('getMe')
        return result

    @gen.coroutine
    def set_webhook(self, url, certificate=None):
        files = None
        if certificate is not None:
            files = {'certificate': certificate}
        result = yield self._fetch('setWebhook', {'url': url}, files)
        return result

    @gen.coroutine
    def send_message(self, chat_id, text, parse_mode=None, reply_markup=None):
        params = {
            'chat_id': chat_id,
            'text': text,
        }
        if parse_mode is not None:
            params['parse_mode'] = parse_mode
        if reply_markup is not None:
            params['reply_markup'] = json.dumps(reply_markup)
        result = yield self._fetch('sendMessage', params)
        return result

    @gen.coroutine
    def edit_message_text(self, chat_id, message_id, text, parse_mode=None,
                          reply_markup=None):
        params = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
        }
        if parse_mode is not None:
            params['parse_mode'] = parse_mode
        if reply_markup is not None:
            params['reply_markup'] = json.dumps(reply_markup)
        result = yield self._fetch('editMessageText', params)
        return result
