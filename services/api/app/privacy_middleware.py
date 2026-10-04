"""Bound private request bodies and disable caching; no cookie authentication."""
import os

from starlette.responses import JSONResponse


class PrivacyMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or not scope['path'].startswith(('/v1/accounts', '/v1/passports', '/v1/goals', '/v1/plans')):
            return await self.app(scope, receive, send)

        async def private_send(message):
            if message['type'] == 'http.response.start':
                headers = [(k, v) for k, v in message.get('headers', []) if k.lower() != b'cache-control']
                message['headers'] = headers + [(b'cache-control', b'no-store'), (b'x-content-type-options', b'nosniff')]
            await send(message)

        # Local debug is explicit. Never trust X-Forwarded-Proto supplied by callers.
        if os.environ.get('APP_ENV') != 'development' and scope['scheme'] != 'https':
            return await JSONResponse({'detail': 'HTTPS required'}, 403)(scope, receive, private_send)
        body = bytearray()
        if scope['method'] in ('POST', 'PUT', 'PATCH'):
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                chunk = message.get('body', b'')
                if len(body) + len(chunk) > 16384:
                    return await JSONResponse({'detail': 'Request too large'}, 413)(scope, receive, private_send)
                body.extend(chunk)
                if not message.get('more_body', False):
                    break

            async def replay():
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}

            return await self.app(scope, replay, private_send)
        await self.app(scope, receive, private_send)
