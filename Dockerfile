FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Instalar Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# ✅ AGREGADO - Instalar ChromeDriver manualmente
RUN CHROME_VERSION=$(google-chrome --version | grep -oP '\d+') \
    && echo "Chrome version: $CHROME_VERSION" \
    && wget -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}.0.0.0/linux64/chromedriver-linux64.zip" \
    && unzip /tmp/chromedriver.zip -d /tmp/ \
    && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && chmod 755 /usr/local/bin/chromedriver \
    && rm -rf /tmp/chromedriver* \
    && chromedriver --version

WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Descargar solo modelos esenciales
RUN python -m spacy download en_core_web_sm \
    && python -m spacy download es_core_news_sm

# Descargar datos de nltk
RUN python -c "import nltk; \
    nltk.download('punkt'); \
    nltk.download('stopwords'); \
    nltk.download('wordnet');"

# ✅ AGREGADO - Crear directorios para Chrome con permisos correctos
RUN mkdir -p /tmp/chrome-user-data \
    && chmod 777 /tmp/chrome-user-data \
    && mkdir -p /app/logs \
    && chmod 777 /app/logs

# ✅ MEJORADO - Crear usuario no-root con grupos adicionales
RUN adduser --disabled-password --gecos '' appuser \
    && usermod -a -G audio,video appuser

# ✅ AGREGADO - Crear directorio de cache y dar permisos
RUN mkdir -p /home/appuser/.cache \
    && mkdir -p /home/appuser/.local \
    && chown -R appuser:appuser /home/appuser

COPY . .
RUN chown -R appuser:appuser /app

# ✅ AGREGADO - Dar permisos de ejecución a Chrome para appuser
RUN chmod 755 /opt/google/chrome/chrome \
    && chmod 755 /usr/bin/google-chrome*

USER appuser

# ✅ AGREGADO - Variables de entorno para Chrome
ENV DISPLAY=:99
ENV CHROME_BIN=/usr/bin/google-chrome-stable
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

EXPOSE 3000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:3000", "--workers", "2", "--timeout", "120", "app.main:app"]