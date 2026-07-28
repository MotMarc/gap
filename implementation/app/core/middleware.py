from __future__ import annotations

import re
import uuid

from starlette.responses import JSONResponse


REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


async def operational_middleware(request, call_next):
    supplied = request.headers.get("X-Request-ID", "")
    request_id = (
        supplied if REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid.uuid4())
    )
    request.state.request_id = request_id
    settings = request.app.state.settings
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.max_request_size:
        response = JSONResponse(
            {
                "error": {
                    "code": "request-too-large",
                    "message": "Request body is too large.",
                    "request_id": request_id,
                }
            },
            status_code=413,
        )
    else:
        response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
