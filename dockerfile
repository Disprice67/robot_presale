FROM python:3.9-slim

WORKDIR /usr/app/src/

RUN mkdir -p /usr/share/man/man1 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    chromium \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY . /usr/app/src/

EXPOSE 8080

RUN pip install --no-cache-dir -r req.txt

CMD ["python", "main.py"]