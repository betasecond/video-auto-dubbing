package oss

import (
	"context"
	"fmt"
	"io"
	"strings"
	"time"

	"vedio/shared/config"

	aliyunoss "github.com/aliyun/aliyun-oss-go-sdk/oss"
)

// Client wraps OSS buckets for internal operations and public signed URLs.
// - bucket: uses cfg.Endpoint for Put/Get/Delete
// - publicBucket: uses cfg.PublicDomain (CNAME) for signed GET URLs
type Client struct {
	bucket       *aliyunoss.Bucket
	publicBucket *aliyunoss.Bucket
	cfg          config.OSSConfig
}

func New(cfg config.OSSConfig) (*Client, error) {
	if cfg.Endpoint == "" {
		return nil, fmt.Errorf("OSS_ENDPOINT is required")
	}
	if cfg.Bucket == "" {
		return nil, fmt.Errorf("OSS_BUCKET is required")
	}
	if cfg.AccessKeyID == "" {
		return nil, fmt.Errorf("OSS_ACCESS_KEY_ID is required")
	}
	if cfg.AccessKeySecret == "" {
		return nil, fmt.Errorf("OSS_ACCESS_KEY_SECRET is required")
	}
	if cfg.PublicDomain == "" {
		return nil, fmt.Errorf("OSS_PUBLIC_DOMAIN is required")
	}

	client, err := aliyunoss.New(
		cfg.Endpoint,
		cfg.AccessKeyID,
		cfg.AccessKeySecret,
		aliyunoss.UseCname(false),
		aliyunoss.Timeout(30, 60),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create OSS client: %w", err)
	}

	publicClient, err := aliyunoss.New(
		cfg.PublicDomain,
		cfg.AccessKeyID,
		cfg.AccessKeySecret,
		aliyunoss.UseCname(true),
		aliyunoss.Timeout(30, 60),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create OSS public client: %w", err)
	}

	bucket, err := client.Bucket(cfg.Bucket)
	if err != nil {
		return nil, fmt.Errorf("failed to open OSS bucket: %w", err)
	}

	publicBucket, err := publicClient.Bucket(cfg.Bucket)
	if err != nil {
		return nil, fmt.Errorf("failed to open OSS public bucket: %w", err)
	}

	return &Client{bucket: bucket, publicBucket: publicBucket, cfg: cfg}, nil
}

func (c *Client) normalizeKey(key string) string {
	key = strings.TrimPrefix(key, "/")
	if c.cfg.Prefix == "" {
		return key
	}
	prefix := strings.Trim(c.cfg.Prefix, "/")
	return prefix + "/" + key
}

func (c *Client) PutObject(ctx context.Context, key string, reader io.Reader, contentType string) error {
	_ = ctx
	key = c.normalizeKey(key)
	opts := []aliyunoss.Option{}
	if contentType != "" {
		opts = append(opts, aliyunoss.ContentType(contentType))
	}
	return c.bucket.PutObject(key, reader, opts...)
}

func (c *Client) GetObject(ctx context.Context, key string) (io.ReadCloser, error) {
	_ = ctx
	key = c.normalizeKey(key)
	return c.bucket.GetObject(key)
}

func (c *Client) DeleteObject(ctx context.Context, key string) error {
	_ = ctx
	key = c.normalizeKey(key)
	return c.bucket.DeleteObject(key)
}

func (c *Client) PresignedGetURL(ctx context.Context, key string, expiry time.Duration) (string, error) {
	_ = ctx
	key = c.normalizeKey(key)
	seconds := int64(expiry.Seconds())
	if seconds <= 0 {
		seconds = 3600
	}
	url, err := c.publicBucket.SignURL(key, aliyunoss.HTTPGet, seconds)
	if err != nil {
		return "", err
	}
	if c.cfg.UseSSL {
		url = strings.Replace(url, "http://", "https://", 1)
	}
	return url, nil
}
