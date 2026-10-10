FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
# Swap in any other LangChain provider package you need (e.g. langchain-anthropic)
ARG EXTRA_PACKAGES="langchain-anthropic"
RUN pip install --no-cache-dir -r requirements.txt ${EXTRA_PACKAGES}

COPY . .

EXPOSE 8000

CMD ["python", "app.py"]
