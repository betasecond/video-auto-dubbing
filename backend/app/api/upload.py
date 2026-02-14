"""
文件上传 API - 预签名 URL 方式
前端直传 OSS，避免后端大文件超时
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services import StorageService
from .deps import get_storage_service

router = APIRouter(prefix="/upload", tags=["upload"])


class PresignRequest(BaseModel):
    filename: str
    content_type: str | None = None


class PresignResponse(BaseModel):
    upload_url: str
    video_key: str
    expires_in: int


@router.post("/presign", response_model=PresignResponse)
def get_presigned_upload_url(
    req: PresignRequest,
    storage_service: StorageService = Depends(get_storage_service),
):
    """
    生成预签名上传 URL，前端直传 OSS

    - **filename**: 原始文件名（用于提取扩展名）
    - **content_type**: MIME 类型（可选）

    Returns:
        - upload_url: 预签名 PUT URL（前端用此 URL 直传文件）
        - video_key: OSS 文件路径（创建任务时传回）
        - expires_in: URL 有效期（秒）
    """
    # 验证文件扩展名
    ext = Path(req.filename).suffix.lower()
    allowed = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".webm"}
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format: {ext}. Allowed: {', '.join(allowed)}",
        )

    # 生成唯一路径：task_<uuid>/input<ext>
    task_id = uuid.uuid4()
    oss_path = f"task_{task_id}/input{ext}"

    expires = 1800  # 30 分钟有效期

    # 生成预签名 PUT URL
    upload_url = storage_service.oss.generate_presigned_url(
        oss_path, expires=expires, method="PUT"
    )

    return PresignResponse(
        upload_url=upload_url,
        video_key=oss_path,
        expires_in=expires,
    )
