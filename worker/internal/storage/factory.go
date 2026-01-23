package storage

import (
	"fmt"

	sharedconfig "vedio/shared/config"
	sharedminio "vedio/shared/minio"
	sharedstorage "vedio/shared/storage"
)

// NewFromConfig creates an ObjectStorage based on STORAGE_BACKEND.
func NewFromConfig(cfg *sharedconfig.BaseConfig) (ObjectStorage, error) {
	backend := cfg.Storage.Backend
	if backend == "" {
		backend = "minio"
	}

	switch backend {
	case "minio":
		minioClient, err := sharedminio.New(cfg.MinIO, sharedminio.WithExistingBucketOnly())
		if err != nil {
			return nil, err
		}
		return sharedstorage.New(minioClient, sharedstorage.WithHostOverride(cfg.MinIO.PublicEndpoint)), nil
	case "oss":
		ossStore, err := sharedstorage.NewOSS(cfg.OSS)
		if err != nil {
			// Fallback to MinIO to keep worker running even before OSS is configured.
			minioClient, mErr := sharedminio.New(cfg.MinIO, sharedminio.WithExistingBucketOnly())
			if mErr != nil {
				return nil, fmt.Errorf("failed to init oss (%v) and failed to init minio fallback (%v)", err, mErr)
			}
			return sharedstorage.New(minioClient, sharedstorage.WithHostOverride(cfg.MinIO.PublicEndpoint)), nil
		}
		return ossStore, nil
	default:
		return nil, fmt.Errorf("unsupported STORAGE_BACKEND: %s", backend)
	}
}
