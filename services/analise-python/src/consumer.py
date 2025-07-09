import json
import os
import logging
import time
from kafka import KafkaConsumer, KafkaProducer
from transformers import pipeline

# --- Configurações ---
# Configura o log para ser mais informativo, incluindo data e hora.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Lê as configurações dos tópicos e do servidor Kafka a partir das variáveis de ambiente.
# Isso torna o serviço configurável sem alterar o código.
KAFKA_SERVER = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC_IN = os.getenv('KAFKA_TOPIC', 'noticias_coletadas')
KAFKA_TOPIC_OUT = os.getenv('KAFKA_ANALYSIS_TOPIC', 'analises_concluidas')

# --- Carregamento do Modelo de PLN ---
# O modelo de análise de sentimento é carregado uma única vez quando o serviço inicia.
# Isso é crucial para a performance, pois o carregamento é um processo pesado.
logger.info("Carregando pipeline de análise de sentimento (Hugging Face)...")
try:
    # 'pipeline' é uma abstração de alto nível da biblioteca 'transformers'
    # que facilita o uso de modelos pré-treinados.
    sentiment_pipeline = pipeline(
        "sentiment-analysis", 
        model="nlptown/bert-base-multilingual-uncased-sentiment"
    )
    logger.info("Pipeline de análise carregado com sucesso.")
except Exception as e:
    logger.critical(f"Falha ao carregar o pipeline de análise: {e}")
    sentiment_pipeline = None # Define como None para que o serviço não inicie com falha.

def classificar_sentimento(resultado_analise):
    """
    Converte o resultado bruto do modelo (que é em "estrelas")
    para nossa classificação simplificada (Positivo, Neutro, Negativo).
    """
    # O resultado é uma lista com um dicionário, ex: [{'label': '4 stars', 'score': 0.8}]
    label = resultado_analise[0]['label']
    score = resultado_analise[0]['score']
    
    if "1 star" in label or "2 stars" in label:
        return "Negativo", score
    if "3 stars" in label:
        return "Neutro", score
    # 4 e 5 estrelas são consideradas Positivo
    return "Positivo", score

# --- Loop Principal do Serviço ---
# O código dentro deste bloco só executa quando o script é chamado diretamente.
if __name__ == "__main__":
    # Verificação de segurança: se o modelo de análise não carregou, o serviço não pode funcionar.
    if not sentiment_pipeline:
        exit(1) # Encerra o container com um código de erro.

    # Inicialização dos clientes Kafka (Consumidor e Produtor)
    consumer = None
    producer = None

    # O serviço tenta se conectar ao Kafka por até 5 vezes antes de desistir.
    # Isso adiciona resiliência contra inicializações lentas do broker Kafka.
    for i in range(5):
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC_IN,
                bootstrap_servers=[KAFKA_SERVER],
                auto_offset_reset='earliest',
                group_id='analise-group-v2', # Usar um novo group_id garante que ele leia mensagens não processadas.
                value_deserializer=lambda v: json.loads(v.decode('utf-8')) # Converte bytes JSON para dicionário Python.
            )

            producer = KafkaProducer(
                bootstrap_servers=[KAFKA_SERVER],
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8') # Converte dicionário para bytes JSON.
            )
            logger.info("Consumidor e Produtor Kafka conectados e prontos.")
            break # Sai do loop se a conexão for bem-sucedida.
        except Exception as e:
            logger.error(f"Falha ao conectar ao Kafka (tentativa {i+1}): {e}")
            time.sleep(5)

    if not consumer or not producer:
        logger.critical("Não foi possível conectar ao Kafka. Encerrando o serviço.")
        exit(1)

    logger.info(f"Ouvindo o tópico '{KAFKA_TOPIC_IN}' e pronto para publicar em '{KAFKA_TOPIC_OUT}'...")
    
    # Este é o loop infinito onde o serviço passa a maior parte do tempo,
    # esperando por novas mensagens no tópico de entrada.
    for message in consumer:
        noticia = message.value
        texto_para_analise = noticia.get("descricao")
        
        # Pula para a próxima mensagem se a notícia não tiver descrição.
        if not texto_para_analise:
            continue

        try:
            # O modelo tem um limite de 512 tokens. Truncamos o texto para evitar erros.
            resultado_analise_raw = sentiment_pipeline(texto_para_analise[:512])
            classificacao, score = classificar_sentimento(resultado_analise_raw)

            # Monta a nova mensagem, combinando os dados originais com a análise.
            mensagem_enriquecida = {
                "noticiaOriginal": noticia,
                "analiseSentimento": {
                    "classificacao": classificacao,
                    "scoreConfianca": score,
                    "labelModelo": resultado_analise_raw[0]['label']
                }
            }

            # Publica a mensagem enriquecida no tópico de saída.
            producer.send(KAFKA_TOPIC_OUT, value=mensagem_enriquecida)
            producer.flush() # Garante que a mensagem seja enviada imediatamente.

            logger.info(f"Análise da notícia '{noticia.get('titulo')}' concluída e publicada.")

        except Exception as e:
            logger.error(f"Erro ao processar ou publicar análise: {e}")