# from uuid import uuid4
# from starlette.requests import Request
# from starlette.responses import Response
# from starlette.middleware.base import RequestResponseEndpoint

# from app.core.logging import request_id_ctx_var


# class CorrelationIdMiddleware:
#     """Attach or generate an X-Request-ID for each request and set it on a contextvar
#     so log records can include it via RequestIdFilter.
#     """

#     async def __call__(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
#         request_id = request.headers.get("x-request-id") or str(uuid4())
#         request_id_ctx_var.set(request_id)
#         response = await call_next(request)
#         response.headers["X-Request-ID"] = request_id
#         return response



from starlette.types import ASGIApp, Receive, Scope, Send
import uuid

class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Only act on HTTP requests
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            correlation_id = headers.get(b"x-correlation-id")

            if correlation_id is None:
                correlation_id = str(uuid.uuid4()).encode()

            scope["headers"].append((b"x-correlation-id", correlation_id))

        await self.app(scope, receive, send)
