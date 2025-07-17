@echo off
echo 启动后端服务...

cd /d "%~dp0\backend"

REM 激活conda环境
call conda activate video_monitor

REM 启动Redis（如果需要）
start "Redis" redis-server

REM 启动Celery Worker
start "Celery Worker" celery -A app.celery_app worker --loglevel=info --pool=solo

REM 启动Flask应用
python run.py

pause
echo ====================================

:: 启动后端API服务
call conda init
call conda activate test_env || (
    echo 错误: 无法激活 conda 环境 "video_monitor"
    pause
    exit /b 1
)
start "后端API服务" cmd /k "cd backend && python run.py --port 5000"

