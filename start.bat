@echo off
chcp 65001 > nul
echo 实时视频监控系统启动脚本
echo ====================================

:: 启动后端
echo 正在激活conda环境...
echo 正在启动后端服务...
cd %~dp0
start cmd /k "chcp 65001 > nul && call conda activate video && cd %~dp0\backend && python run.py --host 0.0.0.0 --port 5000"

:: 等待后端启动
echo 等待后端启动 (5秒)...
timeout /t 5 /nobreak > nul

:: 启动前端
echo 正在启动前端服务...
cd %~dp0\frontend\realtime-monitor-fronted
start cmd /k "chcp 65001 > nul && cd %~dp0\frontend\realtime-monitor-fronted && npm run dev"

echo ====================================
echo 服务已启动:
echo 前端: http://localhost:5175
echo 后端: http://localhost:5000/api/status
echo ====================================

:: 返回到根目录
cd %~dp0