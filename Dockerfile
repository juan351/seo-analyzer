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

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Descargar modelos de spacy para múltiples idiomas
RUN python -m spacy download en_core_web_sm    # Inglés
RUN python -m spacy download es_core_news_sm    # Español
RUN python -m spacy download fr_core_news_sm    # Francés (opcional)
RUN python -m spacy download de_core_news_sm    # Alemán (opcional)

# Descargar datos de nltk para múltiples idiomas
RUN python -c "import nltk; \
    nltk.download('punkt'); \
    nltk.download('stopwords'); \
    nltk.download('wordnet'); \
    nltk.download('punkt_tab');"

COPY . .

EXPOSE 3000

# Usar gunicorn para producción
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app.main:app"]
