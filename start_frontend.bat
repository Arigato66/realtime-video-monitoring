@echo off
echo 启动前端服务...
cd frontend\realtime-monitor-fronted
start "前端服务" cmd /k "npm run dev"
echo 前端服务已启动: http://localhost:5173@echo off
echo 启动前端服务...
echo ====================================

:: 启动前端
cd frontend\realtime-monitor-fronted
start cmd /k "npm run dev"

echo ====================================
echo 前端服务已启动: http://localhost:5173