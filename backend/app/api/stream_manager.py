from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

class StreamConfig(BaseModel):
    name: str
    rtmp_url: str
    description: Optional[str] = None
    detection_modes: List[str] = ["object_detection"]
    danger_zones: Optional[List[dict]] = None

class StreamResponse(BaseModel):
    stream_id: str
    name: str
    rtmp_url: str
    status: str  # active, inactive, error
    created_at: datetime
    last_activity: Optional[datetime]
    detection_modes: List[str]

class StreamManager:
    def __init__(self):
        self.active_streams = {}
        self.stream_configs = {}
    
    async def add_stream(self, config: StreamConfig) -> str:
        """添加新的视频流"""
        stream_id = str(uuid.uuid4())
        
        # 验证RTMP URL连接性
        if not await self._validate_rtmp_url(config.rtmp_url):
            raise HTTPException(status_code=400, detail="无法连接到RTMP流")
        
        # 保存流配置
        self.stream_configs[stream_id] = {
            "id": stream_id,
            "name": config.name,
            "rtmp_url": config.rtmp_url,
            "description": config.description,
            "detection_modes": config.detection_modes,
            "danger_zones": config.danger_zones or [],
            "status": "inactive",
            "created_at": datetime.now(),
            "last_activity": None
        }
        
        return stream_id
    
    async def start_stream(self, stream_id: str):
        """启动视频流处理"""
        if stream_id not in self.stream_configs:
            raise HTTPException(status_code=404, detail="视频流不存在")
        
        # 启动Celery任务
        from app.tasks.video_processing import process_rtmp_stream
        task = process_rtmp_stream.delay(stream_id, self.stream_configs[stream_id])
        
        self.active_streams[stream_id] = {
            "task_id": task.id,
            "status": "active",
            "started_at": datetime.now()
        }
        
        self.stream_configs[stream_id]["status"] = "active"
        
    async def stop_stream(self, stream_id: str):
        """停止视频流处理"""
        if stream_id in self.active_streams:
            # 停止Celery任务
            from app.tasks.video_processing import process_rtmp_stream
            task_id = self.active_streams[stream_id]["task_id"]
            process_rtmp_stream.AsyncResult(task_id).revoke(terminate=True)
            
            del self.active_streams[stream_id]
            self.stream_configs[stream_id]["status"] = "inactive"
    
    async def _validate_rtmp_url(self, rtmp_url: str) -> bool:
        """验证RTMP URL的有效性"""
        import cv2
        cap = cv2.VideoCapture(rtmp_url)
        is_valid = cap.isOpened()
        cap.release()
        return is_valid

# FastAPI路由
stream_manager = StreamManager()

@app.post("/api/streams", response_model=dict)
async def create_stream(config: StreamConfig):
    """创建新的视频流"""
    stream_id = await stream_manager.add_stream(config)
    return {"stream_id": stream_id, "status": "created"}

@app.get("/api/streams", response_model=List[StreamResponse])
async def list_streams():
    """获取所有视频流列表"""
    return list(stream_manager.stream_configs.values())

@app.post("/api/streams/{stream_id}/start")
async def start_stream(stream_id: str):
    """启动视频流处理"""
    await stream_manager.start_stream(stream_id)
    return {"status": "started"}

@app.post("/api/streams/{stream_id}/stop")
async def stop_stream(stream_id: str):
    """停止视频流处理"""
    await stream_manager.stop_stream(stream_id)
    return {"status": "stopped"}

@app.delete("/api/streams/{stream_id}")
async def delete_stream(stream_id: str):
    """删除视频流"""
    await stream_manager.stop_stream(stream_id)
    if stream_id in stream_manager.stream_configs:
        del stream_manager.stream_configs[stream_id]
    return {"status": "deleted"}