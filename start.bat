@echo off
echo 实时视频监控系统启动脚本
echo ====================================

:: 启动后端API服务
call conda init
call conda activate test_env || (
    echo 错误: 无法激活 conda 环境 "video_monitor"
    pause
    exit /b 1
)
start "后端API服务" cmd /k "cd backend && python run.py --port 5000"


:: 启动前端
echo 正在启动前端服务...
cd frontend\realtime-monitor-fronted
start "前端服务" cmd /k "npm run dev"

echo ====================================
echo 服务已启动:
echo 前端: http://localhost:5173
echo 后端: http://localhost:5000/api/status
echo ====================================

:: 返回到根目录
cd ..\.. 