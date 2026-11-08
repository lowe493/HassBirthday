"""v0.3.3 attachment download tests with fake aiohttp session."""
from test_retrieval import att
import asyncio
import json

class Response:
    def __init__(self, status=200, data=b'{}', location=None):
        self.status = status
        self.headers = {'Location':location} if location else {}
        self.content_length = len(data)
        self.content = self
        self.data = data
    async def read(self, n):
        return self.data[:n]
    async def __aenter__(self): return self
    async def __aexit__(self, *a): pass

class Session:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []
    def get(self, url, auth=None, **kwargs):
        self.calls.append((url, auth, kwargs))
        return next(self.responses)

ORIGIN = 'p171-caldav.icloud.com'

def run(coro): return asyncio.run(coro)

def test_external_icloud_unauthed():
    session = Session([Response(data=b'{"date_of_birth":"08/11/1980"}')])
    data,status = run(att._get_json(session, 'https://p55-attachments.icloud.com/file', 'SECRET_AUTH', ORIGIN))
    assert status == 'loaded'
    assert data['date_of_birth'] == '08/11/1980'
    assert session.calls[0][1] is None

def test_same_calendar_host_authed():
    session=Session([Response()])
    assert run(att._get_json(session, 'https://p171-caldav.icloud.com/resource', 'AUTH', ORIGIN))[1] == 'loaded'
    assert session.calls[0][1] == 'AUTH'

def test_redirect_to_icloud_without_auth():
    session=Session([Response(status=302,location='https://p55-attachments.icloud.com/asset'),Response()])
    assert run(att._get_json(session, 'https://p171-caldav.icloud.com/r', 'AUTH', ORIGIN))[1] == 'loaded'
    assert [call[1] for call in session.calls] == ['AUTH',None]

def test_redirect_outside_apple_rejected():
    session=Session([Response(status=302,location='https://example.com/steal')])
    assert run(att._get_json(session, 'https://p171-caldav.icloud.com/r', 'AUTH', ORIGIN))[1] == 'unsafe_attachment_redirect'
    assert len(session.calls) == 1

def test_non_apple_rejected():
    session=Session([])
    assert run(att._get_json(session, 'https://evilicloud.com/file', 'AUTH', ORIGIN))[1] == 'unsafe_attachment_url'
    assert not session.calls

def test_too_large():
    session=Session([Response(data=b'A'*(att.MAX_JSON_BYTES+1))])
    assert run(att._get_json(session, 'https://p55-attachments.icloud.com/file', 'AUTH', ORIGIN))[1] == 'attachment_too_large'

def test_http_error():
    session=Session([Response(status=403)])
    assert run(att._get_json(session, 'https://p55-attachments.icloud.com/file', 'AUTH', ORIGIN))[1] == 'attachment_http_403'
