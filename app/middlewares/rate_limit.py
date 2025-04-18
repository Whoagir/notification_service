# app/middlewares/rate_limit.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import time
from starlette.middleware.base import BaseHTTPMiddleware  # Изменено здесь


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, rate_limit_per_minute: int = 60):
        super().__init__(app)
        self.rate_limit = rate_limit_per_minute
        self.clients = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = time.time()

        if client_ip in self.clients:
            self.clients[client_ip] = [t for t in self.clients[client_ip] if current_time - t < 60]
        else:
            self.clients[client_ip] = []

        if len(self.clients[client_ip]) >= self.rate_limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."}
            )

        self.clients[client_ip].append(current_time)

        return await call_next(request)