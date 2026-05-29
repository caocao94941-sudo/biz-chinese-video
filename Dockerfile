FROM python:3.12-slim

# System deps: ffmpeg, Chinese fonts (no Chromium needed - using Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Init DB with seed data
RUN python scripts/init_db.py

# Create Excel templates
RUN python scripts/create_excel_template.py

EXPOSE 5000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--timeout", "300", "--workers", "2"]
