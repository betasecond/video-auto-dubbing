#!/usr/bin/env python
"""查询最新任务的 ASR 识别结果"""

import asyncio
from app.database import AsyncSessionLocal
from app.models.task import Task
from app.models.segment import Segment
from sqlalchemy import select, desc


async def show_asr_results():
    async with AsyncSessionLocal() as db:
        # 获取最新任务
        result = await db.execute(select(Task).order_by(desc(Task.created_at)).limit(1))
        task = result.scalar_one_or_none()

        if not task:
            print("❌ 没有找到任务")
            return

        print(f"📋 任务ID: {task.id}")
        print(f"📊 状态: {task.status}")
        print(f"🔢 分段数: {task.segment_count}")
        print(f"⏱️  视频时长: {task.video_duration_ms}ms ({task.video_duration_ms/1000:.1f}s)")
        print(f"🌍 翻译: {task.source_language} → {task.target_language}\n")

        # 获取所有分段
        seg_result = await db.execute(
            select(Segment)
            .where(Segment.task_id == task.id)
            .order_by(Segment.segment_index)
        )
        segments = seg_result.scalars().all()

        print(f"=== ASR 识别结果（共 {len(segments)} 条）===\n")

        for seg in segments[:20]:  # 显示前20条
            duration_ms = seg.end_time_ms - seg.start_time_ms
            print(f"[{seg.segment_index:02d}] {seg.start_time_ms/1000:6.2f}s - {seg.end_time_ms/1000:6.2f}s ({duration_ms:5d}ms)")
            print(f"     原文: {seg.original_text}")
            if seg.translated_text:
                print(f"     译文: {seg.translated_text}")
            if seg.speaker_id:
                print(f"     说话人: {seg.speaker_id}")
            print()

        if len(segments) > 20:
            print(f"... 还有 {len(segments) - 20} 条分段未显示")


if __name__ == "__main__":
    asyncio.run(show_asr_results())
