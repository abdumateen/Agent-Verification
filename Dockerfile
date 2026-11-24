FROM ghcr.io/astral-sh/uv:0.12.7 AS uv
FROM python:3.12.7-slim
WORKDIR /opt/app
COPY --from=uv /uv /bin/uv
COPY pyproject.toml uv.lock /opt/app/
COPY src /opt/app/src
COPY tests /opt/app/tests
COPY examples /opt/app/examples
COPY policies /opt/app/policies
COPY acceptance /opt/app/acceptance
COPY Makefile requirements.lock .python-version /opt/app/
ENV PYTHONPATH=/opt/app/src PYTHONDONTWRITEBYTECODE=1 PATH="/opt/app/.venv/bin:$PATH"
RUN uv sync --frozen --extra mcp --no-dev && python -m unittest discover -s tests -v
USER 65534:65534
CMD ["python", "-m", "verifygate.cli", "--help"]
