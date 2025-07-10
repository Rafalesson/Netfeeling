package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"github.com/confluentinc/confluent-kafka-go/v2/kafka"
)

// A função que lida com requisições HTTP permanece a mesma por enquanto.
func handler(w http.ResponseWriter, r *http.Request) {
	log.Println("Endpoint raiz da API Go foi acessado.")
	fmt.Fprintf(w, "API Dashboard em Go está de pé e consumindo do Kafka!")
}

// Função para iniciar o consumidor Kafka em uma goroutine.
func iniciarConsumidor() {
	// Lê as configurações do Kafka a partir de variáveis de ambiente.
	kafkaServer := os.Getenv("KAFKA_BOOTSTRAP_SERVERS")
	topic := os.Getenv("KAFKA_ANALYSIS_TOPIC")
	groupID := "api-go-group"

	// Configura e cria o consumidor.
	consumer, err := kafka.NewConsumer(&kafka.ConfigMap{
		"bootstrap.servers": kafkaServer,
		"group.id":          groupID,
		"auto.offset.reset": "earliest",
	})

	if err != nil {
		log.Fatalf("Falha ao criar o consumidor Kafka: %s", err)
	}

	// Inscreve o consumidor no tópico desejado.
	consumer.SubscribeTopics([]string{topic}, nil)
	log.Printf("Consumidor Kafka inscrito no tópico '%s'", topic)

	// Canal para receber sinais do sistema operacional para um desligamento gracioso.
	sigchan := make(chan os.Signal, 1)
	signal.Notify(sigchan, syscall.SIGINT, syscall.SIGTERM)

	run := true
	for run {
		select {
		case <-sigchan:
			log.Println("Recebido sinal de interrupção, desligando consumidor...")
			run = false
		default:
			// Espera por uma mensagem por até 100ms.
			ev := consumer.Poll(100)
			if ev == nil {
				continue
			}

			switch e := ev.(type) {
			case *kafka.Message:
				// Mensagem recebida! Por enquanto, apenas imprimimos no console.
				log.Printf("==> Mensagem recebida do Kafka:\n%s\n", string(e.Value))
			case kafka.Error:
				// Erros do Kafka (ex: desconexão)
				log.Printf("%% Erro no Kafka: %v\n", e)
				run = false
			}
		}
	}

	log.Println("Fechando o consumidor Kafka...")
	consumer.Close()
}


func main() {
	// Inicia o consumidor Kafka para rodar em paralelo (em uma goroutine).
	// O 'go' na frente da chamada da função faz isso acontecer.
	go iniciarConsumidor()

	// O servidor web continua rodando na goroutine principal.
	http.HandleFunc("/", handler)
	log.Println("Servidor Go iniciado na porta 8081...")
	err := http.ListenAndServe(":8081", nil)
	if err != nil {
		log.Fatal("Erro ao iniciar o servidor: ", err)
	}
}