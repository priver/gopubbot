import codecs
import io
import mimetypes
import os.path
import uuid
from collections import OrderedDict


DEFAULT_MIME_TYPE = 'application/octet-stream'


stream_writer = codecs.getwriter('utf-8')


def render_headers(headers):
    lines = []
    for name, value in headers.items():
        lines.append('{}: {}'.format(name, value))
    lines.append('\r\n')
    return '\r\n'.join(lines).encode('utf-8')


def encode_multipart_formdata(params, files, boundary=None):
    """Encode a params and files using the multipart/form-data MIME format."""
    body = io.BytesIO()
    if boundary is None:
        boundary = 'GoPubBotBoundary{}'.format(uuid.uuid4().hex)

    for name, value in params.items():
        headers = OrderedDict([
            ('Content-Disposition', 'form-data; name="{}"'.format(name)),
        ])
        body.write('--{}\r\n'.format(boundary).encode('utf-8'))
        body.write(render_headers(headers))

        if isinstance(value, (int, float)):
            value = str(value)
        elif isinstance(value, bool):
            value = 'true' if value else 'false'

        stream_writer(body).write(value)
        body.write(b'\r\n')

    for name, file_path in files.items():
        file_name = os.path.basename(file_path)
        headers = OrderedDict([
            (
                'Content-Disposition',
                'form-data; name="{}"; filename="{}"'.format(name, file_name)
            ),
            (
                'Content-Type',
                mimetypes.guess_type(file_path)[0] or DEFAULT_MIME_TYPE
            ),
        ])
        body.write('--{}\r\n'.format(boundary).encode('utf-8'))
        body.write(render_headers(headers))

        with open(file_path, 'rb') as f:
            body.write(f.read())
        body.write(b'\r\n')

    body.write('--{}--\r\n'.format(boundary).encode('utf-8'))

    content_type = 'multipart/form-data; boundary={}'.format(boundary)

    return body.getvalue(), content_type
