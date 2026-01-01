package worker

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"time"

	"vedio/worker/internal/models"

	"github.com/google/uuid"
	"go.uber.org/zap"
)

// processExtractAudio processes the extract_audio step.
func (w *Worker) processExtractAudio(ctx context.Context, taskID uuid.UUID, msg models.TaskMessage) error {
	// Parse payload
	payloadBytes, _ := json.Marshal(msg.Payload)
	var payload models.ExtractAudioPayload
	if err := json.Unmarshal(payloadBytes, &payload); err != nil {
		return fmt.Errorf("failed to parse payload: %w", err)
	}

	w.logger.Info("Extracting audio",
		zap.String("task_id", taskID.String()),
		zap.String("source_video_key", payload.SourceVideoKey),
		zap.String("output_audio_key", payload.OutputAudioKey),
	)

	// Download video from MinIO
	videoReader, err := w.storage.GetObject(ctx, payload.SourceVideoKey)
	if err != nil {
		return fmt.Errorf("failed to get video: %w", err)
	}
	defer videoReader.Close()

	// Create temporary video file
	videoPath := fmt.Sprintf("/tmp/%s_video.mp4", taskID)
	videoFile, err := os.Create(videoPath)
	if err != nil {
		return fmt.Errorf("failed to create temp file: %w", err)
	}
	defer os.Remove(videoPath)
	defer videoFile.Close()

	if _, err := io.Copy(videoFile, videoReader); err != nil {
		return fmt.Errorf("failed to write video: %w", err)
	}
	videoFile.Close()

	// Extract audio using ffmpeg
	audioPath := fmt.Sprintf("/tmp/%s_audio.wav", taskID)
	cmd := exec.CommandContext(ctx, w.config.FFmpeg.Path,
		"-i", videoPath,
		"-vn",           // No video
		"-acodec", "pcm_s16le", // PCM 16-bit
		"-ar", "22050",  // Sample rate
		"-ac", "1",      // Mono
		"-y",            // Overwrite
		audioPath,
	)

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("ffmpeg failed: %w", err)
	}
	defer os.Remove(audioPath)

	// Upload audio to MinIO
	audioFile, err := os.Open(audioPath)
	if err != nil {
		return fmt.Errorf("failed to open audio: %w", err)
	}
	defer audioFile.Close()

	stat, err := audioFile.Stat()
	if err != nil {
		return fmt.Errorf("failed to stat audio: %w", err)
	}

	if err := w.storage.PutObject(ctx, payload.OutputAudioKey, audioFile, stat.Size(), "audio/wav"); err != nil {
		return fmt.Errorf("failed to upload audio: %w", err)
	}

	// Publish next step (ASR)
	asrMsg := map[string]interface{}{
		"task_id":    taskID.String(),
		"step":       "asr",
		"attempt":    1,
		"trace_id":   uuid.New().String(),
		"created_at": time.Now().Format(time.RFC3339),
		"payload": map[string]interface{}{
			"audio_key":  payload.OutputAudioKey,
			"language":   "zh", // TODO: Get from task
			"output_key": fmt.Sprintf("asr/%s/asr.json", taskID),
		},
	}

	if err := w.publisher.Publish(ctx, "task.asr", asrMsg); err != nil {
		return fmt.Errorf("failed to publish asr task: %w", err)
	}

	return nil
}

// processASR processes the asr step.
func (w *Worker) processASR(ctx context.Context, taskID uuid.UUID, msg models.TaskMessage) error {
	// Parse payload
	payloadBytes, _ := json.Marshal(msg.Payload)
	var payload models.ASRPayload
	if err := json.Unmarshal(payloadBytes, &payload); err != nil {
		return fmt.Errorf("failed to parse payload: %w", err)
	}

	w.logger.Info("Processing ASR",
		zap.String("task_id", taskID.String()),
		zap.String("audio_key", payload.AudioKey),
	)

	// TODO: Call VolcEngine ASR API
	// For now, return mock result
	asrResult := models.ASRResult{
		Segments: []models.ASRSegment{
			{Idx: 0, StartMs: 0, EndMs: 1500, Text: "你好，世界"},
			{Idx: 1, StartMs: 1500, EndMs: 3000, Text: "这是一个测试"},
		},
		Language:   payload.Language,
		DurationMs: 3000,
	}

	// Save ASR result to MinIO
	resultJSON, _ := json.Marshal(asrResult)
	resultReader := bytes.NewReader(resultJSON)
	if err := w.storage.PutObject(ctx, payload.OutputKey, resultReader, int64(len(resultJSON)), "application/json"); err != nil {
		return fmt.Errorf("failed to save ASR result: %w", err)
	}

	// Save segments to database
	for _, seg := range asrResult.Segments {
		query := `
			INSERT INTO segments (task_id, idx, start_ms, end_ms, duration_ms, src_text, created_at, updated_at)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
			ON CONFLICT (task_id, idx) DO UPDATE
			SET start_ms = EXCLUDED.start_ms, end_ms = EXCLUDED.end_ms,
			    duration_ms = EXCLUDED.duration_ms, src_text = EXCLUDED.src_text,
			    updated_at = EXCLUDED.updated_at
		`
		now := time.Now()
		_, err := w.db.ExecContext(ctx, query,
			taskID, seg.Idx, seg.StartMs, seg.EndMs, seg.EndMs-seg.StartMs,
			seg.Text, now, now,
		)
		if err != nil {
			return fmt.Errorf("failed to save segment: %w", err)
		}
	}

	// Publish translate task
	// Get all segment IDs
	var segmentIDs []string
	rows, err := w.db.QueryContext(ctx, "SELECT idx FROM segments WHERE task_id = $1 ORDER BY idx", taskID)
	if err != nil {
		return fmt.Errorf("failed to get segments: %w", err)
	}
	defer rows.Close()

	for rows.Next() {
		var idx int
		if err := rows.Scan(&idx); err != nil {
			continue
		}
		segmentIDs = append(segmentIDs, fmt.Sprintf("seg-%d", idx))
	}

	translateMsg := map[string]interface{}{
		"task_id":    taskID.String(),
		"step":       "translate",
		"attempt":    1,
		"trace_id":   uuid.New().String(),
		"created_at": time.Now().Format(time.RFC3339),
		"payload": map[string]interface{}{
			"task_id":         taskID.String(),
			"segment_ids":     segmentIDs,
			"source_language": payload.Language,
			"target_language": "en", // TODO: Get from task
		},
	}

	if err := w.publisher.Publish(ctx, "task.translate", translateMsg); err != nil {
		return fmt.Errorf("failed to publish translate task: %w", err)
	}

	return nil
}

// processTranslate processes the translate step.
func (w *Worker) processTranslate(ctx context.Context, taskID uuid.UUID, msg models.TaskMessage) error {
	// Parse payload
	payloadBytes, _ := json.Marshal(msg.Payload)
	var payload models.TranslatePayload
	if err := json.Unmarshal(payloadBytes, &payload); err != nil {
		return fmt.Errorf("failed to parse payload: %w", err)
	}

	w.logger.Info("Processing translation",
		zap.String("task_id", taskID.String()),
		zap.Int("segment_count", len(payload.SegmentIDs)),
	)

	// Get segments from database
	query := `SELECT idx, src_text FROM segments WHERE task_id = $1 ORDER BY idx`
	rows, err := w.db.QueryContext(ctx, query, taskID)
	if err != nil {
		return fmt.Errorf("failed to get segments: %w", err)
	}
	defer rows.Close()

	type segment struct {
		idx     int
		srcText string
	}
	var segments []segment

	for rows.Next() {
		var s segment
		if err := rows.Scan(&s.idx, &s.srcText); err != nil {
			continue
		}
		segments = append(segments, s)
	}

	// TODO: Call GLM translation API
	// For now, use mock translation
	for _, seg := range segments {
		var translatedText string
		switch seg.srcText {
		case "你好，世界":
			translatedText = "Hello, world"
		case "这是一个测试":
			translatedText = "This is a test"
		default:
			translatedText = seg.srcText // Fallback
		}

		// Update segment with translation
		updateQuery := `UPDATE segments SET mt_text = $1, updated_at = $2 WHERE task_id = $3 AND idx = $4`
		if _, err := w.db.ExecContext(ctx, updateQuery, translatedText, time.Now(), taskID, seg.idx); err != nil {
			return fmt.Errorf("failed to update segment: %w", err)
		}
	}

	// Publish TTS tasks for each segment
	for _, seg := range segments {
		ttsMsg := map[string]interface{}{
			"task_id":    taskID.String(),
			"step":       "tts",
			"attempt":    1,
			"trace_id":   uuid.New().String(),
			"created_at": time.Now().Format(time.RFC3339),
			"payload": map[string]interface{}{
				"task_id":           taskID.String(),
				"segment_id":        fmt.Sprintf("seg-%d", seg.idx),
				"segment_idx":        seg.idx,
				"text":               translatedText,
				"target_duration_ms": 1500, // TODO: Calculate from segment duration
				"speaker_id":         "default",
			},
		}

		if err := w.publisher.Publish(ctx, "task.tts", ttsMsg); err != nil {
			w.logger.Error("Failed to publish TTS task", zap.Error(err), zap.Int("segment_idx", seg.idx))
			// Continue with other segments
		}
	}

	return nil
}

// processTTS processes the tts step.
func (w *Worker) processTTS(ctx context.Context, taskID uuid.UUID, msg models.TaskMessage) error {
	// Parse payload
	payloadBytes, _ := json.Marshal(msg.Payload)
	var payload models.TTSPayload
	if err := json.Unmarshal(payloadBytes, &payload); err != nil {
		return fmt.Errorf("failed to parse payload: %w", err)
	}

	w.logger.Info("Processing TTS",
		zap.String("task_id", taskID.String()),
		zap.Int("segment_idx", payload.SegmentIdx),
	)

	// TODO: Call TTS service
	// For now, create a placeholder
	audioKey := fmt.Sprintf("tts/%s/segment_%d.wav", taskID, payload.SegmentIdx)

	// Update segment with TTS audio key
	updateQuery := `UPDATE segments SET tts_audio_key = $1, updated_at = $2 WHERE task_id = $3 AND idx = $4`
	if _, err := w.db.ExecContext(ctx, updateQuery, audioKey, time.Now(), taskID, payload.SegmentIdx); err != nil {
		return fmt.Errorf("failed to update segment: %w", err)
	}

	// Check if all segments have TTS audio
	var count int
	if err := w.db.QueryRowContext(ctx,
		"SELECT COUNT(*) FROM segments WHERE task_id = $1 AND tts_audio_key IS NULL",
		taskID,
	).Scan(&count); err != nil {
		return fmt.Errorf("failed to check segments: %w", err)
	}

	// If all segments are done, publish mux_video task
	if count == 0 {
		// Get task info
		var sourceVideoKey string
		if err := w.db.QueryRowContext(ctx,
			"SELECT source_video_key FROM tasks WHERE id = $1",
			taskID,
		).Scan(&sourceVideoKey); err != nil {
			return fmt.Errorf("failed to get task: %w", err)
		}

		muxMsg := map[string]interface{}{
			"task_id":    taskID.String(),
			"step":       "mux_video",
			"attempt":    1,
			"trace_id":   uuid.New().String(),
			"created_at": time.Now().Format(time.RFC3339),
			"payload": map[string]interface{}{
				"task_id":         taskID.String(),
				"source_video_key": sourceVideoKey,
				"tts_audio_key":    fmt.Sprintf("tts/%s/dub.wav", taskID), // TODO: Merge all segments
				"output_video_key": fmt.Sprintf("outputs/%s/final.mp4", taskID),
			},
		}

		if err := w.publisher.Publish(ctx, "task.mux_video", muxMsg); err != nil {
			return fmt.Errorf("failed to publish mux_video task: %w", err)
		}
	}

	return nil
}

// processMuxVideo processes the mux_video step.
func (w *Worker) processMuxVideo(ctx context.Context, taskID uuid.UUID, msg models.TaskMessage) error {
	// Parse payload
	payloadBytes, _ := json.Marshal(msg.Payload)
	var payload models.MuxVideoPayload
	if err := json.Unmarshal(payloadBytes, &payload); err != nil {
		return fmt.Errorf("failed to parse payload: %w", err)
	}

	w.logger.Info("Processing video muxing",
		zap.String("task_id", taskID.String()),
		zap.String("source_video_key", payload.SourceVideoKey),
		zap.String("tts_audio_key", payload.TTSAudioKey),
	)

	// TODO: Download video and audio, merge using ffmpeg, upload result
	// For now, just mark task as done
	if err := w.updateTaskStatus(ctx, taskID, "done", nil); err != nil {
		return fmt.Errorf("failed to update task status: %w", err)
	}

	// Update output video key
	updateQuery := `UPDATE tasks SET output_video_key = $1, updated_at = $2 WHERE id = $3`
	if _, err := w.db.ExecContext(ctx, updateQuery, payload.OutputVideoKey, time.Now(), taskID); err != nil {
		return fmt.Errorf("failed to update task: %w", err)
	}

	return nil
}

