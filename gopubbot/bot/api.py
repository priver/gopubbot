import logging
import urllib.parse

import simplejson as json
from tornado import gen
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.httputil import HTTPHeaders

from ..utils.multipart import encode_multipart_formdata
from .exceptions import BotApiError


class BotApiClient(object):
    """Telegram Bot API client."""

    def __init__(self, token):
        self._http_client = AsyncHTTPClient(force_instance=True)
        self.api_url = 'https://api.telegram.org/bot{token}/{{method}}'.format(
            token=token
        )

    def parse_response(self, response):
        data = json.loads(response.body)
        logging.debug(data)
        if not data['ok']:
            raise BotApiError(data['description'])
        return data['result']

    @gen.coroutine
    def fetch(self, method, params=None, files=None):
        url = self.api_url.format(method=method)
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
        return self.parse_response(response)

    @gen.coroutine
    def get_me(self):
        return (yield self.fetch('getMe'))

    @gen.coroutine
    def set_webhook(self, url, certificate=None):
        files = None
        if certificate is not None:
            files = {'certificate': certificate}
        return (yield self.fetch('setWebhook', {'url': url}, files))

    @gen.coroutine
    def send_message(self, chat_id, text, parse_mode=None,
                     disable_web_page_preview=None, disable_notification=None,
                     reply_to_message_id=None, reply_markup=None):
        params = {
            'chat_id': chat_id,
            'text': text,
        }
        if parse_mode is not None:
            params['parse_mode'] = parse_mode
        if disable_web_page_preview is not None:
            params['disable_web_page_preview'] = disable_web_page_preview
        if disable_notification is not None:
            params['disable_notification'] = disable_notification
        if reply_to_message_id is not None:
            params['reply_to_message_id'] = reply_to_message_id
        if reply_markup is not None:
            params['reply_markup'] = json.dumps(reply_markup)
        return (yield self.fetch('sendMessage', params))

    @gen.coroutine
    def edit_message_text(self, text, chat_id=None, message_id=None,
                          message=None, inline_message_id=None,
                          parse_mode=None, disable_web_page_preview=None,
                          reply_markup=None):
        params = {
            'text': text,
        }
        if inline_message_id is not None:
            params['inline_message_id'] = inline_message_id
        elif message is not None:
            params['chat_id'] = message['chat']['id']
            params['message_id'] = message['message_id']
        elif chat_id is not None and message_id is not None:
            params['chat_id'] = chat_id
            params['message_id'] = message_id
        else:
            raise TypeError('You must specify inline_message_id, '
                            'message object or both chat_id and message_id')
        if parse_mode is not None:
            params['parse_mode'] = parse_mode
        if disable_web_page_preview is not None:
            params['disable_web_page_preview'] = disable_web_page_preview
        if reply_markup is not None:
            params['reply_markup'] = json.dumps(reply_markup)
        return (yield self.fetch('editMessageText', params))

    @gen.coroutine
    def answer_inline_query(self, inline_query_id, results, cache_time=None,
                            is_personal=None, next_offset=None,
                            switch_pm_text=None, switch_pm_parameter=None):
        params = {
            'inline_query_id': inline_query_id,
            'results': json.dumps(results),
        }
        if cache_time is not None:
            params['cache_time'] = cache_time
        if is_personal is not None:
            params['is_personal'] = is_personal
        if next_offset is not None:
            params['next_offset'] = next_offset
        if switch_pm_text is not None:
            params['switch_pm_text'] = switch_pm_text
        if switch_pm_parameter is not None:
            params['switch_pm_parameter'] = switch_pm_parameter
        return (yield self.fetch('answerInlineQuery', params))
