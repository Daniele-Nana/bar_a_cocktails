FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN pip install pytest pytest-asyncio rich
# Commande par défaut pour lancer les tests
CMD ["pytest", "tests/", "-v"]