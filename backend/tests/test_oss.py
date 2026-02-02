"""
OSS 客户端集成测试
"""

import tempfile
from pathlib import Path

import pytest

from app.integrations.oss import OSSClient


@pytest.fixture
def oss_client():
    """OSS 客户端 fixture"""
    return OSSClient()


def test_oss_upload_download_bytes(oss_client: OSSClient):
    """测试上传和下载字节数据"""
    test_data = b"Hello, OSS!"
    test_path = "test/integration_test.txt"

    # 上传
    key = oss_client.upload_bytes(test_data, test_path, content_type="text/plain")
    assert key.endswith(test_path)

    # 下载
    downloaded = oss_client.download_bytes(test_path)
    assert downloaded == test_data

    # 清理
    oss_client.delete_file(test_path)


def test_oss_upload_download_file(oss_client: OSSClient):
    """测试上传和下载文件"""
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Test file content")
        temp_file = f.name

    try:
        test_path = "test/integration_file_test.txt"

        # 上传
        key = oss_client.upload_file(temp_file, test_path)
        assert key.endswith(test_path)

        # 下载到新文件
        download_path = temp_file + ".downloaded"
        oss_client.download_file(test_path, download_path)

        # 验证内容
        with open(download_path, "r") as f:
            content = f.read()
        assert content == "Test file content"

        # 清理
        oss_client.delete_file(test_path)
        Path(download_path).unlink()

    finally:
        Path(temp_file).unlink()


def test_oss_file_exists(oss_client: OSSClient):
    """测试文件存在性检查"""
    test_path = "test/exists_test.txt"

    # 文件不存在
    assert not oss_client.file_exists(test_path)

    # 上传文件
    oss_client.upload_bytes(b"test", test_path)

    # 文件存在
    assert oss_client.file_exists(test_path)

    # 清理
    oss_client.delete_file(test_path)

    # 文件不存在
    assert not oss_client.file_exists(test_path)


def test_oss_generate_presigned_url(oss_client: OSSClient):
    """测试生成预签名 URL"""
    test_path = "test/presigned_test.txt"

    # 上传文件
    oss_client.upload_bytes(b"test content", test_path)

    try:
        # 生成签名 URL
        url = oss_client.generate_presigned_url(test_path, expires=300)

        # 验证 URL 格式
        assert "http" in url
        assert test_path in url or "presigned_test.txt" in url
        assert "Expires=" in url or "x-oss-expires=" in url

    finally:
        # 清理
        oss_client.delete_file(test_path)


def test_oss_public_url(oss_client: OSSClient):
    """测试获取公网 URL"""
    test_path = "test/public_url_test.txt"

    # 生成公网 URL（不需要实际上传）
    url = oss_client.get_public_url(test_path)

    # 验证 URL 格式
    assert "http" in url
    assert "test/public_url_test.txt" in url or "public_url_test.txt" in url


def test_oss_get_file_size(oss_client: OSSClient):
    """测试获取文件大小"""
    test_path = "test/size_test.txt"
    test_data = b"12345678901234567890"  # 20 bytes

    # 上传文件
    oss_client.upload_bytes(test_data, test_path)

    try:
        # 获取文件大小
        size = oss_client.get_file_size(test_path)
        assert size == len(test_data)

    finally:
        # 清理
        oss_client.delete_file(test_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
