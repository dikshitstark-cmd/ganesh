FROM python:3.12-slim

# WeasyPrint needs Pango/Cairo/GDK-Pixbuf at the OS level; fonts-noto-core
# gives it a local static Noto Sans Telugu so bulk PDF generation renders
# Telugu correctly without depending on a remote webfont at build/run time.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python generate_placeholders.py

ENV PORT=5000
EXPOSE 5000

CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60
