package service

import "errors"

var (
	// ErrTaskNotFound is returned when a task is not found.
	ErrTaskNotFound = errors.New("task not found")
	// ErrTaskNotCompleted is returned when a task is not completed.
	ErrTaskNotCompleted = errors.New("task not completed")
)

