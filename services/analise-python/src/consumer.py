import json
import os
import logging
import time
from kafka import KafkaConsumer
from transformers import pipeline

# --- Configurações ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

KAFKA_SERVER = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'noticias_coletadas')

# --- Carregamento do Pipeline de Análise de Sentimento ---
# Isso é feito uma única vez. A biblioteca 'transformers' baixa e gerencia o modelo.
# O modelo 'nlptown/bert-base-multilingual-uncased-sentiment' entende várias línguas, incluindo português.
logger.info("Carregando pipeline de análise de sentimento (Hugging Face)...")
try:
    sentiment_pipeline = pipeline(
        "sentiment-analysis", 
        model="nlptown/bert-base-multilingual-uncased-sentiment"
    )
    logger.info("Pipeline de análise carregado com sucesso.")
except Exception as e:
    logger.critical(f"Falha ao carregar o pipeline de análise: {e}")
    sentiment_pipeline = None

def classificar_sentimento(resultado_analise):
    """Converte o resultado do modelo (estrelas) para nossa classificação."""
    label = resultado_analise[0]['label']
    score = resultado_analise[0]['score']
    
    if "1 star" in label or "2 stars" in label:
        return "Negativo", score
    if "3 stars" in label:
        return "Neutro", score
    # 4 e 5 estrelas
    return "Positivo", score

# --- Loop Principal do Consumidor ---
if __name__ == "__main__":
    if not sentiment_pipeline:
        exit(1) # Encerra o serviço se o modelo não carregou

    consumer = None
    # (O bloco de conexão com o Kafka permanece o mesmo da versão anterior)
    for i in range(5):
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=[KAFKA_SERVER],
                auto_offset_reset='earliest',
                group_id='analise-group-v2', # Mudamos o group_id para garantir que ele releia o tópico
                value_deserializer=lambda v: json.loads(v.decode('utf-8'))
            )
            logger.info("Consumidor Kafka conectado e pronto.")
            break
        except Exception as e:
            logger.error(f"Falha ao conectar consumidor ao Kafka (tentativa {i+1}): {e}")
            time.sleep(5)

    if not consumer:
        logger.critical("Não foi possível conectar ao Kafka. Encerrando o serviço.")
        exit(1)

    logger.info(f"Ouvindo o tópico '{KAFKA_TOPIC}' para análise com Transformer...")
    for message in consumer:
        noticia = message.value
        texto_para_analise = noticia.get("descricao")
        
        if not texto_para_analise:
            continue

        try:
            # O modelo pode ter um limite de 512 tokens. Truncamos o texto para garantir.
            resultado = sentiment_pipeline(texto_para_analise[:512])
            
            classificacao, score = classificar_sentimento(resultado)

            logger.info(
                f"--- ANÁLISE CONCLUÍDA (BERT) ---\n"
                f"  Título: {noticia.get('titulo')}\n"
                f"  Score de Confiança: {score:.4f}\n"
                f"  Classificação: {classificacao} ({resultado[0]['label']})\n"
            )
        except Exception as e:
            logger.error(f"Erro ao analisar o texto: {e}")