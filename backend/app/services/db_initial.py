import mysql.connector
from app.config import config
import uuid
from werkzeug.security import generate_password_hash
import os


def init_database():
    """初始化数据库和表结构"""
    try:
        # 获取当前环境配置
        config_name = os.environ.get('FLASK_CONFIG', 'development')
        current_config = config[config_name]()
        
        # 检查是否为生产环境或云环境（修改这里）
        if config_name in ['production', 'cloud']:
            # 创建数据库连接
            conn = mysql.connector.connect(
                host=current_config.MYSQL_HOST,
                port=current_config.MYSQL_PORT,
                user=current_config.MYSQL_USER,
                password=current_config.MYSQL_PASSWORD
            )
            cursor = conn.cursor()
            
            # 创建数据库（如果不存在）
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {current_config.MYSQL_DB} DEFAULT CHARSET {current_config.MYSQL_CHARSET}")
            cursor.execute(f"USE {current_config.MYSQL_DB}")
            
            print(f"✅ 连接到MySQL数据库: {current_config.MYSQL_DB}")
            print(f"✅ 当前环境: {config_name}")
        else:
            print("ℹ️  开发环境使用SQLite数据库，无需初始化MySQL")
            return
        
        # 创建位置表（如果不存在）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            location_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '位置ID(UUID)',
            location_name VARCHAR(100) NOT NULL COMMENT '位置名称',
            address TEXT COMMENT '详细地址',
            location_type VARCHAR(50) COMMENT '位置类型(室内/室外等)',
            description TEXT COMMENT '位置描述'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 创建摄像头设备表（如果不存在）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cameras (
            camera_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '摄像头ID(UUID)',
            location_id VARCHAR(36) NOT NULL COMMENT '安装位置ID',
            camera_type VARCHAR(50) NOT NULL COMMENT '摄像头类型',
            model_number VARCHAR(50) COMMENT '设备型号',
            ip_address VARCHAR(50) COMMENT 'IP地址',
            installation_date DATE COMMENT '安装日期',
            last_maintenance_date DATE COMMENT '最后维护日期',
            status VARCHAR(20) DEFAULT 'active' COMMENT '设备状态',
            FOREIGN KEY (location_id) REFERENCES locations(location_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 新增：插入默认位置记录（关键）
        cursor.execute("SELECT COUNT(*) FROM locations WHERE location_id = 'default_location'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
            INSERT INTO locations (
                location_id, location_name, address, location_type, description
            ) VALUES (
                'default_location', '默认监控区域', '未指定地址', '室内', '系统自动创建的默认监控位置'
            )
            """)
            conn.commit()
            print("✅ 已插入默认位置记录")

        # 新增：插入默认摄像头记录（关键）
        cursor.execute("SELECT COUNT(*) FROM cameras WHERE camera_id = 'default_camera'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
            INSERT INTO cameras (
                camera_id, location_id, camera_type, model_number, status
            ) VALUES (
                'default_camera', 'default_location', 'behavior_monitoring', '默认型号', 'active'
            )
            """)
            conn.commit()
            print("✅ 已插入默认摄像头记录")


        # 创建乘客表（无错误）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS passengers (
            passenger_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '乘客唯一标识符(UUID)',
            id_card_number VARCHAR(18) UNIQUE COMMENT '身份证号码',
            name VARCHAR(50) NOT NULL COMMENT '乘客姓名',
            gender CHAR(1) COMMENT '性别(M-男, F-女)',
            birth_date DATE COMMENT '出生日期',
            phone_number VARCHAR(20) COMMENT '联系电话',
            registered_face_feature JSON COMMENT '人脸特征向量(JSON格式)',
            registration_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
            blacklist_flag BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否在黑名单中',
            blacklist_reason TEXT COMMENT '加入黑名单的原因',
            image_path VARCHAR(255) COMMENT '注册人脸的图像文件路径',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        

        # 创建人脸识别记录表（无错误）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS face_recognition_logs (
            recognition_id VARCHAR(36) PRIMARY KEY COMMENT '识别记录ID(UUID)',
            passenger_id VARCHAR(36) COMMENT '匹配到的乘客ID',
            camera_id VARCHAR(36) NOT NULL COMMENT '摄像头ID',
            recognition_time DATETIME NOT NULL COMMENT '识别时间',
            confidence_score FLOAT COMMENT '识别置信度(0-1)',
            matched_face_feature BLOB COMMENT '识别时提取的人脸特征',
            location_id VARCHAR(36) NOT NULL COMMENT '识别位置ID',
            image_path VARCHAR(255) COMMENT '抓拍图像存储路径',
            FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id),
            FOREIGN KEY (location_id) REFERENCES locations(location_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 创建行为检测记录表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS behavior_detection_logs (
            detection_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '行为检测ID(UUID)',
            passenger_id VARCHAR(36) COMMENT '关联乘客ID',
            camera_id VARCHAR(36) NOT NULL COMMENT '摄像头ID',
            detection_time DATETIME NOT NULL COMMENT '检测时间',
            behavior_type VARCHAR(50) NOT NULL COMMENT '检测到的行为类型',
            confidence_score FLOAT COMMENT '检测置信度(0-1)',
            risk_level VARCHAR(20) COMMENT '风险等级(low/medium/high)',
            location_id VARCHAR(36) NOT NULL COMMENT '检测位置ID',
            detection_area VARCHAR(50)  COMMENT '监测区域',
            FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id),
            FOREIGN KEY (camera_id) REFERENCES cameras(camera_id),
            FOREIGN KEY (location_id) REFERENCES locations(location_id) 
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 创建报警记录表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '报警ID(UUID)',
            detection_id VARCHAR(36) COMMENT '关联的行为检测ID',
            alert_time DATETIME NOT NULL COMMENT '报警时间',
            alert_type VARCHAR(50) NOT NULL COMMENT '报警类型(blacklist_match/high_risk_behavior)',
            severity VARCHAR(20) COMMENT '严重程度(critical/high/medium/low)',
            status VARCHAR(20) DEFAULT 'unprocessed' COMMENT '处理状态(unprocessed/processing/resolved)',
            camera_id VARCHAR(36) COMMENT '摄像头ID',
            location_id VARCHAR(36) COMMENT '位置ID',
            message TEXT COMMENT '告警消息',
            FOREIGN KEY (detection_id) REFERENCES behavior_detection_logs(detection_id)  
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 危险区域表（无错误）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS danger_zone_config (
        id INT AUTO_INCREMENT PRIMARY KEY,
        location_id VARCHAR(36) NOT NULL COMMENT '位置ID',
        danger_zone JSON NOT NULL COMMENT '危险区域坐标',
        safety_distance INT DEFAULT 100 COMMENT '安全距离',
        loitering_threshold FLOAT DEFAULT 2.0 COMMENT '停留时间阈值',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 新增用户表（无错误）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '用户唯一标识符(UUID)',
            username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
            password VARCHAR(255) NOT NULL COMMENT '密码哈希值',
            email VARCHAR(100) NOT NULL UNIQUE COMMENT '邮箱',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            last_login TIMESTAMP NULL COMMENT '最后登录时间',
            is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '账户是否激活'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("✅ 数据库表创建成功!")
        
        # 检查并创建默认管理员用户
        check_query = "SELECT COUNT(*) FROM users WHERE username = 'admin'"
        cursor.execute(check_query)
        count = cursor.fetchone()[0]

        if count == 0:
            admin_user_id = str(uuid.uuid4())
            hashed_password = generate_password_hash('123')
            
            insert_query = """
            INSERT INTO users (user_id, username, password, email, is_active)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (admin_user_id, 'admin', hashed_password, 'admin@example.com', True))
            conn.commit()
            print("✅ 默认管理员用户创建成功 (用户名: admin, 密码: 123)")
        else:
            print("ℹ️  管理员用户已存在")
            
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as e:
        print(f"❌ 数据库初始化失败: {e}")
        raise
    except Exception as e:
        print(f"❌ 初始化过程中发生错误: {e}")
        raise