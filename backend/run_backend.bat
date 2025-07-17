@echo off
echo 正在激活conda环境...
call conda activate video_monitor || (
    echo 激活conda环境失败，尝试使用pip安装依赖...
    pip install -r requirements.txt
)

echo 正在启动后端服务...
cd %~dp0
python run.py --host 0.0.0.0 --port 5000

pause 