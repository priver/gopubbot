from .handlers.webhook import WebHookHandler

url_patterns = [
    (r'/webhook/(?P<token>[^\/]+)', WebHookHandler),
]
