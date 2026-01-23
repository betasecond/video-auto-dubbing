package tts

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"path/filepath"
	"time"

	"vedio/shared/config"

	"go.uber.org/zap"
)

// GradioClient handles TTS API calls to Gradio-based IndexTTS services.
// It interfaces with the Gradio API endpoints for IndexTTS2.
type GradioClient struct {
	baseURL string
	apiKey  string
	client  *http.Client
	logger  *zap.Logger
}

// NewGradioClient creates a new Gradio TTS client.
func NewGradioClient(cfg config.TTSConfig, logger *zap.Logger) *GradioClient {
	return &GradioClient{
		baseURL: cfg.URL,
		apiKey:  cfg.APIKey,
		client: &http.Client{
			Timeout: 600 * time.Second,
		},
		logger: logger,
	}
}

// GradioFileData represents a file uploaded to Gradio.
type GradioFileData struct {
	Path     string                 `json:"path"`
	URL      string                 `json:"url,omitempty"`
	Size     int                    `json:"size,omitempty"`
	OrigName string                 `json:"orig_name,omitempty"`
	MimeType string                 `json:"mime_type,omitempty"`
	IsStream bool                   `json:"is_stream"`
	Meta     map[string]interface{} `json:"meta"`
}

// GradioSynthesizeRequest represents the Gradio API request.
type GradioSynthesizeRequest struct {
	Data      []interface{} `json:"data"`
	EventData interface{}   `json:"event_data,omitempty"`
	FnIndex   int          `json:"fn_index,omitempty"`
	SessionHash string     `json:"session_hash,omitempty"`
}

// GradioSynthesizeResponse represents the Gradio API response.
type GradioSynthesizeResponse struct {
	Data     []interface{} `json:"data"`
	IsGenerating bool      `json:"is_generating,omitempty"`
	Duration     float64   `json:"duration,omitempty"`
	AvgDuration  float64   `json:"average_duration,omitempty"`
}

// Synthesize performs TTS synthesis using the Gradio IndexTTS API.
func (c *GradioClient) Synthesize(ctx context.Context, req SynthesisRequest) (io.ReadCloser, error) {
	c.logger.Info("Starting Gradio TTS synthesis",
		zap.String("text", req.Text),
		zap.String("speaker_id", req.SpeakerID),
		zap.String("prompt_audio_url", req.PromptAudioURL),
	)

	// Call the gen_single endpoint directly with OSS URL
	// Gradio can download remote audio files automatically
	audioFile, err := c.callGenSingle(ctx, req, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to call gen_single: %w", err)
	}

	// Step 3: Download the generated audio
	audioReader, err := c.downloadGeneratedAudio(ctx, audioFile)
	if err != nil {
		return nil, fmt.Errorf("failed to download generated audio: %w", err)
	}

	c.logger.Info("Gradio TTS synthesis completed successfully")
	return audioReader, nil
}

// uploadAudioFile uploads an audio file to Gradio for use as prompt audio.
func (c *GradioClient) uploadAudioFile(ctx context.Context, audioURL string) (*GradioFileData, error) {
	// First, download the audio file
	audioReq, err := http.NewRequestWithContext(ctx, "GET", audioURL, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create audio download request: %w", err)
	}

	audioResp, err := c.client.Do(audioReq)
	if err != nil {
		return nil, fmt.Errorf("failed to download audio: %w", err)
	}
	defer audioResp.Body.Close()

	if audioResp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to download audio: status %d", audioResp.StatusCode)
	}

	audioData, err := io.ReadAll(audioResp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read audio data: %w", err)
	}

	// Create multipart form for file upload
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)

	// Add file part
	filename := "prompt_audio.wav"
	if ext := filepath.Ext(audioURL); ext != "" {
		filename = "prompt_audio" + ext
	}

	filePart, err := writer.CreateFormFile("files", filename)
	if err != nil {
		return nil, fmt.Errorf("failed to create file part: %w", err)
	}

	if _, err := filePart.Write(audioData); err != nil {
		return nil, fmt.Errorf("failed to write audio data: %w", err)
	}

	if err := writer.Close(); err != nil {
		return nil, fmt.Errorf("failed to close multipart writer: %w", err)
	}

	// Upload to Gradio
	uploadURL := fmt.Sprintf("%s/gradio_api/upload", c.baseURL)
	uploadReq, err := http.NewRequestWithContext(ctx, "POST", uploadURL, &buf)
	if err != nil {
		return nil, fmt.Errorf("failed to create upload request: %w", err)
	}

	uploadReq.Header.Set("Content-Type", writer.FormDataContentType())
	if c.apiKey != "" {
		uploadReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.apiKey))
	}

	uploadResp, err := c.client.Do(uploadReq)
	if err != nil {
		return nil, fmt.Errorf("failed to upload file: %w", err)
	}
	defer uploadResp.Body.Close()

	if uploadResp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(uploadResp.Body)
		return nil, fmt.Errorf("upload failed with status %d: %s", uploadResp.StatusCode, string(body))
	}

	// Parse upload response
	var uploadResult []string
	if err := json.NewDecoder(uploadResp.Body).Decode(&uploadResult); err != nil {
		return nil, fmt.Errorf("failed to decode upload response: %w", err)
	}

	if len(uploadResult) == 0 {
		return nil, fmt.Errorf("upload response is empty")
	}

	// Create file data object
	filePath := uploadResult[0]
	fileData := &GradioFileData{
		Path:     filePath,
		URL:      fmt.Sprintf("%s/file=%s", c.baseURL, filePath),
		OrigName: filename,
		MimeType: "audio/wav",
		IsStream: false,
		Meta:     map[string]interface{}{"_type": "gradio.FileData"},
	}

	return fileData, nil
}

// callGenSingle calls the Gradio /gen_single API endpoint.
func (c *GradioClient) callGenSingle(ctx context.Context, req SynthesisRequest, promptFile *GradioFileData) (*GradioFileData, error) {
	// Prepare API request parameters
	// Based on the API info, gen_single expects these parameters:
	data := make([]interface{}, 24) // 24 parameters total (from API spec)

	// Parameter 0: emo_control_method (default: "与音色参考音频相同")
	data[0] = "与音色参考音频相同"

	// Parameter 1: prompt (audio file for voice reference)
	// Use promptAudioURL directly as Gradio can handle remote URLs
	if req.PromptAudioURL != "" {
		data[1] = map[string]interface{}{
			"path": req.PromptAudioURL,
			"url":  req.PromptAudioURL,
			"meta": map[string]interface{}{"_type": "gradio.FileData"},
		}
	} else {
		data[1] = nil
	}

	// Parameter 2: text (required)
	data[2] = req.Text

	// Parameter 3: emo_ref_path (emotion reference audio)
	data[3] = nil

	// Parameter 4: emo_weight (default: 0.8)
	data[4] = 0.8

	// Parameters 5-12: emotion vectors (vec1-vec8, all default to 0.0)
	for i := 5; i <= 12; i++ {
		data[i] = 0.0
	}

	// Parameter 13: emo_text (emotion description text)
	data[13] = ""

	// Parameter 14: emo_random (emotion random sampling)
	data[14] = false

	// Parameter 15: max_text_tokens_per_sentence (default: 120)
	data[15] = 120

	// Parameter 16: do_sample (default: true)
	data[16] = true

	// Parameter 17: top_p (default: 0.8)
	data[17] = 0.8

	// Parameter 18: top_k (default: 30)
	data[18] = 30

	// Parameter 19: temperature (default: 0.8)
	data[19] = 0.8

	// Parameter 20: length_penalty (default: 0.0)
	data[20] = 0.0

	// Parameter 21: num_beams (default: 3)
	data[21] = 3

	// Parameter 22: repetition_penalty (default: 10.0)
	data[22] = 10.0

	// Parameter 23: max_mel_tokens (default: 1500)
	data[23] = 1500

	gradioReq := GradioSynthesizeRequest{
		Data:        data,
		EventData:   nil,
		FnIndex:     0, // This may need to be adjusted based on the actual API
		SessionHash: fmt.Sprintf("session_%d", time.Now().Unix()),
	}

	reqBody, err := json.Marshal(gradioReq)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	// Call the API
	apiURL := fmt.Sprintf("%s/gradio_api/run/gen_single", c.baseURL)
	httpReq, err := http.NewRequestWithContext(ctx, "POST", apiURL, bytes.NewReader(reqBody))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")
	if c.apiKey != "" {
		httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.apiKey))
	}

	resp, err := c.client.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("API request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API returned status %d: %s", resp.StatusCode, string(body))
	}

	// Parse response
	var gradioResp GradioSynthesizeResponse
	if err := json.NewDecoder(resp.Body).Decode(&gradioResp); err != nil {
		return nil, fmt.Errorf("failed to decode API response: %w", err)
	}

	// Extract audio file from response data
	if len(gradioResp.Data) == 0 {
		return nil, fmt.Errorf("no data in API response")
	}

	// The response structure is: data[0] = {visible: true, value: {FileData}, __type__: "update"}
	var audioFile *GradioFileData

	// Try to extract from wrapped response (data[0].value)
	if wrapped, ok := gradioResp.Data[0].(map[string]interface{}); ok {
		if value, ok := wrapped["value"].(map[string]interface{}); ok {
			audioFile = &GradioFileData{
				IsStream: false,
				Meta:     map[string]interface{}{"_type": "gradio.FileData"},
			}
			if path, ok := value["path"].(string); ok {
				audioFile.Path = path
			}
			if url, ok := value["url"].(string); ok {
				audioFile.URL = url
			}
			if origName, ok := value["orig_name"].(string); ok {
				audioFile.OrigName = origName
			}
			if mimeType, ok := value["mime_type"].(string); ok {
				audioFile.MimeType = mimeType
			}
		}
	}

	// Fallback: try direct FileData format
	if audioFile == nil {
		audioData, ok := gradioResp.Data[0].(map[string]interface{})
		if !ok {
			return nil, fmt.Errorf("unexpected response format: %T", gradioResp.Data[0])
		}

		audioFile = &GradioFileData{
			IsStream: false,
			Meta:     map[string]interface{}{"_type": "gradio.FileData"},
		}
		if path, ok := audioData["path"].(string); ok {
			audioFile.Path = path
		}
		if url, ok := audioData["url"].(string); ok {
			audioFile.URL = url
		}
		if origName, ok := audioData["orig_name"].(string); ok {
			audioFile.OrigName = origName
		}
		if mimeType, ok := audioData["mime_type"].(string); ok {
			audioFile.MimeType = mimeType
		}
	}

	// Gradio returns paths like "/gradio_api/file=/tmp/gradio/xxx.wav"
	// If the path already contains the full URL endpoint, use it as-is
	// Otherwise, construct the correct download URL
	if audioFile.URL == "" && audioFile.Path != "" {
		// If path already starts with /gradio_api/file=, prepend base URL
		if len(audioFile.Path) > 0 && audioFile.Path[0] == '/' {
			audioFile.URL = fmt.Sprintf("%s%s", c.baseURL, audioFile.Path)
		} else {
			// Otherwise, construct the gradio file endpoint
			audioFile.URL = fmt.Sprintf("%s/gradio_api/file=%s", c.baseURL, audioFile.Path)
		}
	}

	return audioFile, nil
}

// downloadGeneratedAudio downloads the generated audio from Gradio.
func (c *GradioClient) downloadGeneratedAudio(ctx context.Context, audioFile *GradioFileData) (io.ReadCloser, error) {
	if audioFile == nil {
		return nil, fmt.Errorf("no audio file provided")
	}

	downloadURL := audioFile.URL
	if downloadURL == "" && audioFile.Path != "" {
		downloadURL = fmt.Sprintf("%s/file=%s", c.baseURL, audioFile.Path)
	}

	if downloadURL == "" {
		return nil, fmt.Errorf("no download URL available")
	}

	c.logger.Debug("Downloading generated audio",
		zap.String("url", downloadURL),
		zap.String("path", audioFile.Path))

	req, err := http.NewRequestWithContext(ctx, "GET", downloadURL, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create download request: %w", err)
	}

	if c.apiKey != "" {
		req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.apiKey))
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to download audio: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		c.logger.Error("Failed to download audio",
			zap.Int("status", resp.StatusCode),
			zap.String("url", downloadURL),
			zap.String("response", string(body)))
		return nil, fmt.Errorf("download failed with status %d: %s", resp.StatusCode, string(body))
	}

	return resp.Body, nil
}