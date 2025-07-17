#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask应用启动脚本
支持通过命令行参数和.env文件配置运行环境

使用方法:
    python run.py                          # 开发模式（默认）
    python run.py --config production      # 生产模式
    python run.py --config cloud          # 云端模式
    python run.py --port 8000             # 指定端口
    python run.py --host 0.0.0.0          # 指定主机
    python run.py --init-db               # 初始化数据库
"""

import os
import sys
import click
from dotenv import load_dotenv

# 设置DeepFace模型下载路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
deepface_home = os.path.join(project_root, 'data', '.deepface_models')
os.environ['DEEPFACE_HOME'] = deepface_home
os.makedirs(deepface_home, exist_ok=True)

# 解决OpenMP警告
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# 加载.env文件
load_dotenv()

# 导入应用模块
try:
    from app import create_app, socketio
    from app.services import db_initial
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保在backend目录下运行此脚本")
    sys.exit(1)

# 支持的配置环境
VALID_CONFIGS = ['development', 'production', 'cloud', 'testing']

@click.command()
@click.option('--config', '-c', 
              type=click.Choice(VALID_CONFIGS), 
              default=None,
              help='配置环境 (development/production/cloud/testing)')
@click.option('--host', '-h', 
              default=None,
              help='服务器主机地址')
@click.option('--port', '-p', 
              type=int, 
              default=None,
              help='服务器端口号')
@click.option('--debug/--no-debug', 
              default=None,
              help='是否启用调试模式')
@click.option('--init-db', 
              is_flag=True,
              help='初始化数据库后退出')
@click.option('--show-config', 
              is_flag=True,
              help='显示当前配置信息后退出')
def main(config, host, port, debug, init_db, show_config):
    """Flask应用启动器"""
    
    # 确定配置环境（优先级：命令行 > 环境变量 > 默认值）
    config_name = config or os.environ.get('FLASK_CONFIG', 'development')
    
    # 设置环境变量
    os.environ['FLASK_CONFIG'] = config_name
    
    # 创建应用实例
    app = create_app(config_name)
    
    # 获取配置对象
    config_obj = app.config
    
    # 确定主机和端口
    if host is None:
        if config_name in ['production', 'cloud']:
            host = os.environ.get('PROD_HOST', '0.0.0.0')
        else:
            host = os.environ.get('DEFAULT_HOST', '127.0.0.1')
    
    if port is None:
        if config_name in ['production', 'cloud']:
            port = int(os.environ.get('PROD_PORT', 5000))
        else:
            port = int(os.environ.get('DEFAULT_PORT', 5000))
    
    # 确定调试模式
    if debug is None:
        debug = config_obj.get('DEBUG', False)
    
    # 显示配置信息
    print("\n" + "="*50)
    print(f"🚀 Flask应用启动器")
    print("="*50)
    print(f"📋 运行环境: {config_name}")
    print(f"🌐 服务地址: http://{host}:{port}")
    print(f"🔧 调试模式: {'开启' if debug else '关闭'}")
    print(f"🗄️  数据库: {config_obj.get('SQLALCHEMY_DATABASE_URI', 'Not configured')[:50]}...")
    print(f"🔐 安全密钥: {'已配置' if config_obj.get('SECRET_KEY') else '未配置'}")
    
    if hasattr(config_obj, 'CORS_ORIGINS'):
        print(f"🌍 CORS来源: {len(config_obj.CORS_ORIGINS)} 个已配置")
    
    print("="*50 + "\n")
    
    # 如果只是显示配置，则退出
    if show_config:
        print("📋 详细配置信息:")
        for key, value in config_obj.items():
            if 'PASSWORD' in key or 'SECRET' in key:
                print(f"  {key}: {'*' * 8}")
            else:
                print(f"  {key}: {value}")
        return
    
    # 如果需要初始化数据库
    if init_db:
        print("🔧 正在初始化数据库...")
        try:
            with app.app_context():
                db_initial.init_database()
            print("✅ 数据库初始化完成")
        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")
            sys.exit(1)
        return
    
    # 启动应用
    try:
        print(f"🎯 启动Flask应用...")
        socketio.run(
            app, 
            host=host, 
            port=port, 
            debug=debug,
            use_reloader=False,  # 避免重复启动
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        print("\n👋 应用已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()