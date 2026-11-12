# ROYEXA, production image (T10b2). Build context: backend/.
FROM python:3.14-slim

RUN pip install --no-cache-dir uv==0.11.32

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN useradd --system --create-home --uid 10001 royexa
WORKDIR /app

# Dependencies first, so a code change does not reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# The code reads the migrations and the pilot directory from beside the source tree.
COPY src ./src
COPY migrations ./migrations
COPY pilot ./pilot
COPY start.sh ./start.sh
RUN uv sync --locked --no-dev && chown -R royexa:royexa /app

USER royexa
EXPOSE 8000
CMD ["sh", "start.sh"]
