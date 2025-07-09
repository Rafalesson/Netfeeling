from fastapi import FastAPI, HTTPException
from kafka import KafkaProducer
import json
import os
import logging
import time
import requests # Biblioteca para fazer requisições HTTP

# --- Configurações ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_SERVER = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'noticias_coletadas')
NEWS_API_KEY = os.getenv('NEWS_API_KEY') # Pega a chave da API

app = FastAPI(title="Serviço Coletor de Notícias")
producer = None

# --- Conexão com o Kafka ---
# (O bloco de conexão com o Kafka permanece o mesmo da versão anterior)
for i in range(5):
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_SERVER],
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8')
        )
        logger.info("Produtor Kafka conectado com sucesso.")
        break
    except Exception as e:
        logger.error(f"Falha ao conectar ao Kafka (tentativa {i+1}): {e}")
        time.sleep(5)

# --- Lógica de Negócio ---
def buscar_noticias(termo: str):
    """Função que busca notícias na NewsAPI."""
    if not NEWS_API_KEY:
        logger.error("Chave da NewsAPI não configurada.")
        return None

    url = f"https://newsapi.org/v2/everything?q={termo}&apiKey={NEWS_API_KEY}&language=pt&sortBy=publishedAt"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            logger.info(f"Notícias sobre '{termo}' buscadas com sucesso.")
            return response.json().get("articles", [])
        else:
            logger.error(f"Erro ao buscar notícias: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exceção ao buscar notícias: {e}")
        return None

# --- Endpoints da API ---
@app.get("/", summary="Verificação de status")
def read_root():
    return {"status": "Serviço Coletor está de pé e conectado ao Kafka" if producer else "Serviço Coletor com falha na conexão com Kafka"}

@app.post("/coletar/{termo}", summary="Inicia a coleta de notícias e envia para o Kafka")
def coletar_noticias(termo: str):
    """
    Endpoint que dispara a busca de notícias por um termo e publica cada artigo no Kafka.
    """
    if not producer:
        raise HTTPException(status_code=503, detail="Serviço indisponível: Produtor Kafka não conectado.")

    artigos = buscar_noticias(termo)

    if artigos is None:
        raise HTTPException(status_code=500, detail="Falha ao buscar notícias da fonte externa.")

    if not artigos:
        return {"status": f"Nenhuma notícia encontrada para o termo '{termo}'."}

    total_enviado = 0
    for artigo in artigos:
        try:
            # Selecionamos apenas os campos que nos interessam
            mensagem = {
                "fonte": artigo.get("source", {}).get("name"),
                "autor": artigo.get("author"),
                "titulo": artigo.get("title"),
                "descricao": artigo.get("description"),
                "url": artigo.get("url"),
                "publicadoEm": artigo.get("publishedAt"),
                "conteudo": artigo.get("content")
            }
            producer.send(KAFKA_TOPIC, value=mensagem)
            total_enviado += 1
        except Exception as e:
            logger.error(f"Erro ao enviar artigo para o Kafka: {e}")

    producer.flush()
    logger.info(f"{total_enviado} notícias sobre '{termo}' enviadas para o Kafka.")
    return {"status": f"{total_enviado} notícias sobre '{termo}' enviadas com sucesso para o tópico {KAFKA_TOPIC}."}