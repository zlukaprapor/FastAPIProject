# Multi-stage build для оптимізації
FROM python:3.11-slim as builder

# Встановлюємо системні залежності для компіляції
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Встановлюємо Python залежності
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as runtime

# Створюємо непривілейованого користувача
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Встановлюємо тільки runtime залежності
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копіюємо встановлені пакети з builder stage
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Копіюємо код застосунку
COPY --chown=appuser:appuser . .

# Налаштовуємо PATH та змінні оточення
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Перемикаємось на непривілейованого користувача
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:4567/health || exit 1

EXPOSE 4567

# Запускаємо застосунок
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4567"]