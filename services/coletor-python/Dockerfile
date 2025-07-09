# 1. Imagem Base: Começamos com uma imagem oficial do Python, versão 3.9.
# A tag '-slim' significa que é uma versão mais leve, o que resulta em uma imagem final menor.
FROM python:3.9-slim

# 2. Diretório de Trabalho: Definimos o diretório de trabalho dentro do container.
# Todos os comandos subsequentes serão executados a partir daqui.
WORKDIR /app

# 3. Copiar e Instalar Dependências: Copiamos APENAS o arquivo de requisitos primeiro.
# O Docker cria camadas, e esta etapa só será executada novamente se o requirements.txt mudar.
# Isso acelera muito as builds futuras.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar Código Fonte: Agora, copiamos o nosso código para o diretório de trabalho no container.
COPY ./src .

# 5. Comando de Execução: Este é o comando que será executado quando o container iniciar.
# Ele inicia o servidor Uvicorn, que executa nossa aplicação FastAPI.
# O host '0.0.0.0' é CRÍTICO para que o serviço seja acessível de fora do container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]