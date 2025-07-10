# --- Estágio 1: Build ---
FROM golang:1.24-bookworm AS builder

# Instala as dependências de build. 'apt-get' é o gerenciador de pacotes do Debian.
RUN apt-get update && apt-get install -y build-essential librdkafka-dev

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod tidy

COPY . .

# Compila o nosso código.
RUN go build -o /app/server .


# --- Estágio 2: Runtime ---
# Usamos uma base 'slim' do Debian para o ambiente final. É leve e compatível.
FROM debian:bookworm-slim

# Instala apenas a biblioteca C 'librdkafka' necessária para a execução.
RUN apt-get update && apt-get install -y librdkafka1 && rm -rf /var/lib/apt/lists/*

WORKDIR /root/

# Copia o binário compilado do estágio de build.
COPY --from=builder /app/server .

EXPOSE 8081

# Executa o nosso servidor.
CMD ["./server"]