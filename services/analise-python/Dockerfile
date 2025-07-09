# 1. Imagem Base
FROM python:3.9-slim

# 2. Diretório de Trabalho
WORKDIR /app

# 3. Instalar Dependências
COPY requirements.txt .
# O pip instalará o spacy e o modelo em português a partir do link no requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar Código Fonte
COPY ./src .

# 5. Comando de Execução:
# Este container não é um servidor web. Ele é um "worker".
# Seu trabalho é rodar um script python continuamente.
CMD ["python", "consumer.py"]