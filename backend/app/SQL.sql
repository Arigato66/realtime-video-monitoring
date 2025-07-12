-- 创建数据库
CREATE DATABASE IF NOT EXISTS station_monitoring_system;
USE station_monitoring_system;

-- 1. 乘客信息表
CREATE TABLE passengers (
    passenger_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '乘客唯一标识符(UUID)',
    id_card_number VARCHAR(18) DEFAULT NULL COMMENT '身份证号码',
    name VARCHAR(50) NOT NULL COMMENT '乘客姓名',
    gender CHAR(1) DEFAULT NULL COMMENT '性别(M-男, F-女)',
    birth_date DATE DEFAULT NULL COMMENT '出生日期',
    phone_number VARCHAR(20) DEFAULT NULL COMMENT '联系电话',
    registered_face_feature BLOB DEFAULT NULL COMMENT '注册的人脸特征向量(64位二进制数据)',
    registration_time DATETIME DEFAULT NULL COMMENT '注册时间',
    blacklist_flag BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否在黑名单中',
    blacklist_reason TEXT DEFAULT NULL COMMENT '加入黑名单的原因',
    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='乘客信息表';

-- 2. 人脸识别记录表
CREATE TABLE face_recognition_logs (
    recognition_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '识别记录ID(UUID)',
    passenger_id VARCHAR(36) DEFAULT NULL COMMENT '匹配到的乘客ID',
    camera_id VARCHAR(36) NOT NULL COMMENT '摄像头ID',
    recognition_time DATETIME NOT NULL COMMENT '识别时间',
    confidence_score FLOAT DEFAULT NULL COMMENT '识别置信度(0-1)',
    matched_face_feature BLOB DEFAULT NULL COMMENT '识别时提取的人脸特征',
    location_id VARCHAR(36) NOT NULL COMMENT '识别位置ID',
    image_path VARCHAR(255) DEFAULT NULL COMMENT '抓拍图像存储路径',
    FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id) ON DELETE SET NULL,
    INDEX idx_recognition_time (recognition_time),
    INDEX idx_camera_recognition (camera_id, recognition_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='人脸识别记录表';

-- 3. 行为检测记录表
CREATE TABLE behavior_detection_logs (
    detection_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '行为检测ID(UUID)',
    passenger_id VARCHAR(36) DEFAULT NULL COMMENT '关联乘客ID',
    camera_id VARCHAR(36) NOT NULL COMMENT '摄像头ID',
    detection_time DATETIME NOT NULL COMMENT '检测时间',
    behavior_type VARCHAR(50) NOT NULL COMMENT '检测到的行为类型',
    confidence_score FLOAT DEFAULT NULL COMMENT '检测置信度(0-1)',
    risk_level VARCHAR(20) DEFAULT NULL COMMENT '风险等级(low/medium/high)',
    location_id VARCHAR(36) NOT NULL COMMENT '检测位置ID',
    video_clip_path VARCHAR(255) DEFAULT NULL COMMENT '视频片段存储路径',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '处理状态',
    handled_by VARCHAR(36) DEFAULT NULL COMMENT '处理人员ID',
    handled_time DATETIME DEFAULT NULL COMMENT '处理时间',
    notes TEXT DEFAULT NULL COMMENT '处理备注',
    FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id) ON DELETE SET NULL,
    INDEX idx_detection_time (detection_time),
    INDEX idx_risk_behavior (risk_level, behavior_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='行为检测记录表';

-- 4. 危险行为分类表
CREATE TABLE dangerous_behaviors (
    behavior_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '行为类型ID(UUID)',
    behavior_name VARCHAR(100) NOT NULL COMMENT '行为名称',
    description TEXT DEFAULT NULL COMMENT '行为详细描述',
    default_risk_level VARCHAR(20) NOT NULL COMMENT '默认风险等级(low/medium/high)',
    model_version VARCHAR(50) DEFAULT NULL COMMENT '检测模型版本',
    UNIQUE KEY uk_behavior_name (behavior_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='危险行为分类表';

-- 5. 车站位置表
CREATE TABLE locations (
    location_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '位置ID(UUID)',
    location_name VARCHAR(100) NOT NULL COMMENT '位置名称',
    location_type VARCHAR(50) NOT NULL COMMENT '位置类型',
    station_id VARCHAR(36) NOT NULL COMMENT '所属车站ID',
    floor_number INT DEFAULT NULL COMMENT '楼层号',
    coordinates VARCHAR(100) DEFAULT NULL COMMENT '坐标信息',
    INDEX idx_station_location (station_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='车站位置表';

-- 6. 车站信息表
CREATE TABLE stations (
    station_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '车站ID(UUID)',
    station_name VARCHAR(100) NOT NULL COMMENT '车站名称',
    city VARCHAR(50) NOT NULL COMMENT '所在城市',
    address TEXT DEFAULT NULL COMMENT '详细地址',
    contact_number VARCHAR(20) DEFAULT NULL COMMENT '车站联系电话',
    UNIQUE KEY uk_station_name_city (station_name, city)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='车站信息表';

-- 7. 摄像头设备表（含推拉流相关字段）
CREATE TABLE cameras (
    camera_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '摄像头ID(UUID)',
    location_id VARCHAR(36) NOT NULL COMMENT '安装位置ID',
    camera_type VARCHAR(50) NOT NULL COMMENT '摄像头类型',
    model_number VARCHAR(50) DEFAULT NULL COMMENT '设备型号',
    ip_address VARCHAR(50) DEFAULT NULL COMMENT 'IP地址',
    installation_date DATE DEFAULT NULL COMMENT '安装日期',
    last_maintenance_date DATE DEFAULT NULL COMMENT '最后维护日期',
    status VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '设备状态',
    -- 推拉流相关字段
    stream_url VARCHAR(255) DEFAULT NULL COMMENT '视频流地址',
    push_protocol VARCHAR(20) DEFAULT 'RTMP' COMMENT '推流协议(RTMP/RTSP/HTTP-FLV)',
    pull_protocol VARCHAR(20) DEFAULT 'HTTP-FLV' COMMENT '拉流协议',
    stream_key VARCHAR(100) DEFAULT NULL COMMENT '流密钥',
    bitrate INT DEFAULT 2048 COMMENT '码率(kbps)',
    resolution VARCHAR(20) DEFAULT '1920x1080' COMMENT '分辨率',
    FOREIGN KEY (location_id) REFERENCES locations(location_id) ON DELETE CASCADE,
    INDEX idx_camera_status (status),
    INDEX idx_stream_url (stream_url)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='摄像头设备表';

-- 8. 报警记录表
CREATE TABLE alerts (
    alert_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '报警ID(UUID)',
    detection_id VARCHAR(36) DEFAULT NULL COMMENT '关联的行为检测ID',
    alert_time DATETIME NOT NULL COMMENT '报警时间',
    alert_type VARCHAR(50) NOT NULL COMMENT '报警类型',
    severity VARCHAR(20) NOT NULL COMMENT '严重程度(critical/high/medium/low)',
    status VARCHAR(20) NOT NULL DEFAULT 'unprocessed' COMMENT '处理状态',
    assigned_to VARCHAR(36) DEFAULT NULL COMMENT '分配给的安全人员ID',
    resolution TEXT DEFAULT NULL COMMENT '处理结果描述',
    resolved_time DATETIME DEFAULT NULL COMMENT '解决时间',
    FOREIGN KEY (detection_id) REFERENCES behavior_detection_logs(detection_id) ON DELETE SET NULL,
    INDEX idx_alert_time (alert_time),
    INDEX idx_alert_severity (severity, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='报警记录表';

-- 9. 安保人员表
CREATE TABLE security_staff (
    staff_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '安保人员ID(UUID)',
    name VARCHAR(50) NOT NULL COMMENT '姓名',
    badge_number VARCHAR(20) NOT NULL COMMENT '工牌编号',
    department VARCHAR(50) DEFAULT NULL COMMENT '所属部门',
    contact_number VARCHAR(20) DEFAULT NULL COMMENT '联系电话',
    shift_schedule TEXT DEFAULT NULL COMMENT '班次安排',
    access_level INT NOT NULL DEFAULT 1 COMMENT '系统访问权限级别',
    UNIQUE KEY uk_badge_number (badge_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='安保人员表';

-- 10. 系统日志表
CREATE TABLE system_logs (
    log_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '日志ID(UUID)',
    log_time DATETIME NOT NULL COMMENT '日志时间',
    log_level VARCHAR(20) NOT NULL COMMENT '日志级别(INFO/WARNING/ERROR等)',
    module VARCHAR(50) NOT NULL COMMENT '模块名称',
    message TEXT NOT NULL COMMENT '日志消息',
    details TEXT DEFAULT NULL COMMENT '详细内容',
    user_id VARCHAR(36) DEFAULT NULL COMMENT '操作用户ID',
    INDEX idx_log_time_level (log_time, log_level),
    INDEX idx_module_log (module, log_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统日志表';

-- 11. 推拉流服务器信息表（新增表）
CREATE TABLE stream_servers (
    server_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '服务器ID(UUID)',
    server_name VARCHAR(100) NOT NULL COMMENT '服务器名称',
    ip_address VARCHAR(50) NOT NULL COMMENT '服务器IP地址',
    port INT NOT NULL DEFAULT 1935 COMMENT '服务端口',
    max_streams INT DEFAULT 100 COMMENT '最大并发流数',
    status VARCHAR(20) NOT NULL DEFAULT 'running' COMMENT '服务器状态(running/stopped/maintenance)',
    protocol_supported VARCHAR(100) DEFAULT 'RTMP,RTSP,HTTP-FLV' COMMENT '支持的协议',
    last_heartbeat DATETIME DEFAULT NULL COMMENT '最后心跳时间',
    UNIQUE KEY uk_server_ip_port (ip_address, port),
    INDEX idx_server_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='推拉流服务器信息表';

-- 12. 流会话记录表（新增表）
CREATE TABLE stream_sessions (
    session_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT '会话ID(UUID)',
    camera_id VARCHAR(36) NOT NULL COMMENT '关联摄像头ID',
    server_id VARCHAR(36) NOT NULL COMMENT '关联服务器ID',
    start_time DATETIME NOT NULL COMMENT '流开始时间',
    end_time DATETIME DEFAULT NULL COMMENT '流结束时间',
    duration INT DEFAULT NULL COMMENT '持续时长(秒)',
    stream_type VARCHAR(10) NOT NULL COMMENT '流类型(push/pull)',
    bandwidth_used FLOAT DEFAULT NULL COMMENT '带宽使用(Mbps)',
    status VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '会话状态(active/ended/error)',
    error_log TEXT DEFAULT NULL COMMENT '错误日志',
    FOREIGN KEY (camera_id) REFERENCES cameras(camera_id) ON DELETE CASCADE,
    FOREIGN KEY (server_id) REFERENCES stream_servers(server_id) ON DELETE CASCADE,
    INDEX idx_session_time (start_time, end_time),
    INDEX idx_camera_session (camera_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='流会话记录表';

-- 添加外键关联（补充安保人员与报警的关联）
ALTER TABLE alerts 
ADD CONSTRAINT fk_alert_staff 
FOREIGN KEY (assigned_to) 
REFERENCES security_staff(staff_id) 
ON DELETE SET NULL;