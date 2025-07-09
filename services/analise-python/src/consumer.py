import json
import os
import logging
import time
from kafka import KafkaConsumer

# --- Configurações ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_SERVER = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'noticias_coletadas')

# --- Loop Principal do Consumidor ---
if __name__ == "__main__":
    consumer = None
    # Tentamos conectar com o Kafka, com retentativas
    for i in range(5):
        try:
            # O 'group_id' é importante. Ele define um grupo de consumidores.
            # O Kafka entrega cada mensagem para apenas um consumidor dentro do mesmo grupo.
            consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=[KAFKA_SERVER],
                auto_offset_reset='earliest', # Começa a ler do início do tópico se for um novo consumidor
                group_id='analise-group',
                # 'value_deserializer' é o inverso do que fizemos no produtor.
                # Ele pega os bytes do Kafka e os transforma de volta em um dicionário Python.
                value_deserializer=lambda v: json.loads(v.decode('utf-8'))
            )
            logger.info("Consumidor Kafka conectado e pronto para receber mensagens.")
            break
        except Exception as e:
            logger.error(f"Falha ao conectar consumidor ao Kafka (tentativa {i+1}): {e}")
            time.sleep(5)

    if not consumer:
        logger.critical("Não foi possível conectar ao Kafka. Encerrando o serviço.")
        exit(1) # Encerra o container se não conseguir conectar

    logger.info(f"Ouvindo o tópico '{KAFKA_TOPIC}'...")
    for message in consumer:
        # message.value já é um dicionário Python graças ao deserializer
        noticia = message.value
        titulo = noticia.get("titulo", "Título não encontrado")
        
        # Por enquanto, apenas imprimimos o título para confirmar o recebimento.
        logger.info(f"--- NOVA NOTÍCIA RECEBIDA --- \nTítulo: {titulo}\n")