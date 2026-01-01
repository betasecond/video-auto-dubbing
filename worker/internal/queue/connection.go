package queue

import (
	"fmt"

	"vedio/worker/internal/config"

	amqp "github.com/rabbitmq/amqp091-go"
)

// Connection wraps the RabbitMQ connection.
type Connection struct {
	*amqp.Connection
}

// NewConnection creates a new RabbitMQ connection.
func NewConnection(cfg config.RabbitMQConfig) (*Connection, error) {
	conn, err := amqp.Dial(cfg.URL)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to RabbitMQ: %w", err)
	}

	return &Connection{conn}, nil
}

// Close closes the RabbitMQ connection.
func (c *Connection) Close() error {
	return c.Connection.Close()
}

