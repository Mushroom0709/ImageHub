"""上传处理进度总线（内存版 SSE）

每个 asset 在后端处理期间，其他订阅者可以实时收到阶段事件：
  - uploaded: OBS 直传完成
  - thumbnail: 缩略图生成+上传
  - exif: EXIF 读取完成
  - ai_tagging: AI 打标完成
  - done / failed: 终态

多订阅者支持（每个订阅者一个 queue）。
"""
import asyncio
import time
from typing import Any


class ProgressBus:
    """简单的内存 pub/sub + 历史缓冲"""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = {}
        self._history: dict[str, list[dict]] = {}  # 历史事件（保留最近 100 条）
        self._lock = asyncio.Lock()

    async def publish(self, asset_id: str, stage: str, payload: dict | None = None):
        """发布一个阶段事件"""
        event = {
            "asset_id": asset_id,
            "stage": stage,
            "ts": time.time(),
            "payload": payload or {},
        }
        async with self._lock:
            # 追加到历史（最多 100 条，重连时回放）
            self._history.setdefault(asset_id, []).append(event)
            self._history[asset_id] = self._history[asset_id][-100:]
            queues = list(self._subscribers.get(asset_id, set()))
        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    async def subscribe(self, asset_id: str) -> asyncio.Queue:
        """订阅一个 asset 的事件流（订阅瞬间先回放历史，避免错过已完成阶段）"""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers.setdefault(asset_id, set()).add(q)
            history = list(self._history.get(asset_id, []))
        # 回放历史到 queue（持锁外，避免阻塞 publisher）
        for ev in history:
            try:
                q.put_nowait(ev)
            except asyncio.QueueFull:
                break
        return q

    async def unsubscribe(self, asset_id: str, q: asyncio.Queue):
        async with self._lock:
            subs = self._subscribers.get(asset_id)
            if subs and q in subs:
                subs.discard(q)
                if not subs:
                    self._subscribers.pop(asset_id, None)


# 全局单例
progress_bus = ProgressBus()