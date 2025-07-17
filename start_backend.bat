@echo off
echo 启动后端服务...
echo ====================================

:: 启动后端API服务
call conda init
call conda activate video_monitor || (
    echo 错误: 无法激活 conda 环境 "video_monitor"
    pause
    exit /b 1
)
start "后端API服务" cmd /k "cd backend && python run.py --port 5000"

