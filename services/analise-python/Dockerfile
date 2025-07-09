# --- Estágio 1: O Construtor (Builder) ---
FROM python:3.9 AS builder

WORKDIR /app

# Atualiza o pip
RUN pip install --upgrade pip

# Copia o arquivo de requisitos
COPY requirements.txt .

# --- Instalação Cirúrgica ---
# 1. Instala a PyTorch (CPU-only) diretamente do seu índice oficial.
#    Isso é mais rápido e confiável do que buscar no índice geral do PyPI.
RUN pip install torch==2.3.1 --index-url https://download.pytorch.org/whl/cpu

# 2. Instala o restante das dependências do nosso arquivo.
RUN pip install --no-cache-dir -r requirements.txt


# --- Estágio 2: O Ambiente Final (Runtime) ---
FROM python:3.9-slim AS runtime

WORKDIR /app

# Copia as bibliotecas instaladas do estágio "builder"
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages

# Copia nosso código-fonte
COPY ./src .

# Comando de execução
CMD ["python", "consumer.py"]