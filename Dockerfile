FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
# Add the LangChain integration for any other provider you use, e.g. langchain-google-genai
ARG EXTRA_PACKAGES="langchain-anthropic"
RUN pip install -r requirements.txt ${EXTRA_PACKAGES}

COPY . .

# Run as an unprivileged user that can only write generated editions
RUN useradd --create-home --uid 10001 newsroom \
    && mkdir -p /app/outputs \
    && chown -R newsroom /app/outputs
USER newsroom

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

CMD ["python", "app.py"]
