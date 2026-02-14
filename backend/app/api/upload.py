"""
文件上传 API - PostObject 签名方式
后端生成 V4 签名，前端用 FormData POST 直传 OSS
"""

import base64
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services import StorageService
from .deps import get_storage_service

router = APIRouter(prefix="/upload", tags=["upload"])


class PresignRequest(BaseModel):
    filename: str


class PresignResponse(BaseModel):
    host: str
    key: str
    policy: str
    x_oss_signature_version: str
    x_oss_credential: str
    x_oss_date: str
    signature: str
    video_key: str


def _hmacsha256(key: bytes, data: str) -> bytes:
    return hmac.new(key, data.encode(), hashlib.sha256).digest()


def _extract_region(endpoint: str) -> str:
    """从 endpoint 提取 region，如 oss-cn-hangzhou.aliyuncs.com -> cn-hangzhou"""
    # 去掉 scheme
    ep = endpoint.replace("https://", "").replace("http://", "")
    # 处理 access point 格式: xxx.oss-cn-hangzhou.oss-accesspoint.aliyuncs.com
    if "oss-accesspoint" in ep:
        parts = ep.split(".")
        for p in parts:
            if p.startswith("oss-") and p != "oss-accesspoint":
                return p.replace("oss-", "")
    # 标准格式: oss-cn-hangzhou.aliyuncs.com
    if ep.startswith("oss-"):
        return ep.split(".")[0].replace("oss-", "")
    return "cn-hangzhou"


@router.post("/presign", response_model=PresignResponse)
def get_post_signature(
    req: PresignRequest,
    storage_service: StorageService = Depends(get_storage_service),
):
    """
    生成 PostObject 签名，前端用 FormData POST 直传 OSS

    Returns:
        - host: OSS Bucket 域名（前端 POST 目标）
        - key: 文件在 OSS 中的完整路径
        - policy, signature 等签名字段
        - video_key: 创建任务时传回的 OSS 相对路径
    """
    ext = Path(req.filename).suffix.lower()
    allowed = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".webm"}
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format: {ext}. Allowed: {', '.join(allowed)}",
        )

    # 生成唯一路径
    task_id = uuid.uuid4()
    # video_key 是相对于 prefix 的路径（给后端 task 用）
    video_key = f"task_{task_id}/input{ext}"
    # full_key 是 OSS 中的完整 key（包含 prefix）
    prefix = settings.oss_prefix.rstrip("/")
    full_key = f"{prefix}/{video_key}" if prefix else video_key

    # 从 endpoint 提取 region
    region = _extract_region(settings.oss_endpoint)
    bucket = settings.oss_bucket
    access_key_id = settings.oss_access_key_id
    access_key_secret = settings.oss_access_key_secret

    # 使用标准 OSS endpoint（不用 access point）
    host = f"https://{bucket}.oss-{region}.aliyuncs.com"

    # 时间
    now = datetime.now(timezone.utc)
    date = now.strftime("%Y%m%d")
    x_oss_date = now.strftime("%Y%m%dT%H%M%SZ")
    # 过期时间：1小时后
    from datetime import timedelta
    expiration = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    # 构建 credential
    x_oss_credential = f"{access_key_id}/{date}/{region}/oss/aliyun_v4_request"

    # 步骤1：构建 policy
    policy_dict = {
        "expiration": expiration,
        "conditions": [
            {"bucket": bucket},
            {"x-oss-signature-version": "OSS4-HMAC-SHA256"},
            {"x-oss-credential": x_oss_credential},
            {"x-oss-date": x_oss_date},
            ["eq", "$key", full_key],
            ["eq", "$success_action_status", "200"],
            ["content-length-range", 1, 500 * 1024 * 1024],  # 最大 500MB
        ],
    }
    policy_json = json.dumps(policy_dict)

    # 步骤2：构造待签名字符串
    string_to_sign = base64.b64encode(policy_json.encode()).decode()

    # 步骤3：计算 SigningKey
    date_key = _hmacsha256(f"aliyun_v4{access_key_secret}".encode(), date)
    date_region_key = _hmacsha256(date_key, region)
    date_region_service_key = _hmacsha256(date_region_key, "oss")
    signing_key = _hmacsha256(date_region_service_key, "aliyun_v4_request")

    # 步骤4：计算 Signature
    signature = _hmacsha256(signing_key, string_to_sign).hex()

    return PresignResponse(
        host=host,
        key=full_key,
        policy=string_to_sign,
        x_oss_signature_version="OSS4-HMAC-SHA256",
        x_oss_credential=x_oss_credential,
        x_oss_date=x_oss_date,
        signature=signature,
        video_key=video_key,
    )
