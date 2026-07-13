FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN useradd --system --uid 10001 --create-home sarmiento
WORKDIR /app/control-plane
COPY control-plane/pyproject.toml ./
COPY control-plane/src ./src
COPY control-plane/migrations ./migrations
COPY control-plane/alembic.ini ./
RUN pip install --upgrade pip && pip install .
COPY control-plane/entrypoint.sh ./entrypoint.sh
COPY front /app/front
COPY agent /app/agent
COPY viewer /app/viewer
RUN chmod 0755 entrypoint.sh && chown -R sarmiento:sarmiento /app
USER sarmiento
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
