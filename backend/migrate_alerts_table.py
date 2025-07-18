#!/usr/bin/env python3
"""
数据库迁移脚本：修复alerts表结构
将现有的alerts表结构更新为与SQLAlchemy模型匹配的结构
"""

import mysql.connector
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import Config

def migrate_alerts_table():
    """迁移alerts表结构"""
    try:
        # 创建数据库连接
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor()
        
        print("开始迁移alerts表结构...")
        
        # 1. 检查现有表是否存在
        cursor.execute("SHOW TABLES LIKE 'alerts'")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            print("发现现有alerts表，正在备份数据...")
            
            # 2. 备份现有数据（如果有的话）
            cursor.execute("SELECT COUNT(*) FROM alerts")
            row_count = cursor.fetchone()[0]
            
            if row_count > 0:
                print(f"发现 {row_count} 条现有数据，创建备份表...")
                cursor.execute("CREATE TABLE alerts_backup AS SELECT * FROM alerts")
                print("数据备份完成")
            
            # 3. 删除现有表
            cursor.execute("DROP TABLE alerts")
            print("已删除旧的alerts表")
        
        # 4. 创建新的alerts表结构
        print("创建新的alerts表结构...")
        cursor.execute("""
        CREATE TABLE alerts (
            id INT AUTO_INCREMENT PRIMARY KEY COMMENT '告警ID(自增)',
            timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '告警时间',
            event_type VARCHAR(50) NOT NULL COMMENT '事件类型',
            details VARCHAR(255) COMMENT '详细信息',
            status VARCHAR(20) DEFAULT 'unprocessed' COMMENT '处理状态(unprocessed/viewed/resolved)',
            video_path VARCHAR(255) COMMENT '视频路径',
            frame_snapshot_path VARCHAR(255) COMMENT '快照路径'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        # 5. 如果有备份数据，尝试迁移兼容的字段
        if table_exists and row_count > 0:
            print("尝试迁移兼容的数据...")
            try:
                # 检查备份表的结构
                cursor.execute("DESCRIBE alerts_backup")
                backup_columns = [row[0] for row in cursor.fetchall()]
                
                # 构建迁移SQL
                migration_fields = []
                if 'alert_time' in backup_columns:
                    migration_fields.append("alert_time as timestamp")
                elif 'timestamp' in backup_columns:
                    migration_fields.append("timestamp")
                else:
                    migration_fields.append("NOW() as timestamp")
                
                if 'alert_type' in backup_columns:
                    migration_fields.append("alert_type as event_type")
                elif 'event_type' in backup_columns:
                    migration_fields.append("event_type")
                else:
                    migration_fields.append("'Unknown' as event_type")
                
                if 'resolution' in backup_columns:
                    migration_fields.append("resolution as details")
                elif 'details' in backup_columns:
                    migration_fields.append("details")
                else:
                    migration_fields.append("NULL as details")
                
                migration_fields.extend([
                    "status",
                    "NULL as video_path",
                    "NULL as frame_snapshot_path"
                ])
                
                migration_sql = f"""
                INSERT INTO alerts (timestamp, event_type, details, status, video_path, frame_snapshot_path)
                SELECT {', '.join(migration_fields)}
                FROM alerts_backup
                """
                
                cursor.execute(migration_sql)
                migrated_count = cursor.rowcount
                print(f"成功迁移 {migrated_count} 条数据")
                
            except Exception as e:
                print(f"数据迁移失败: {e}")
                print("新表结构已创建，但旧数据未能迁移")
        
        conn.commit()
        print("✅ alerts表迁移完成！")
        
        # 6. 显示新表结构
        cursor.execute("DESCRIBE alerts")
        columns = cursor.fetchall()
        print("\n新的alerts表结构:")
        for col in columns:
            print(f"  {col[0]} - {col[1]} - {col[2]} - {col[3]} - {col[4]} - {col[5]}")
        
        return True
        
    except mysql.connector.Error as err:
        print(f"❌ 迁移失败: {err}")
        return False
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    print("=== alerts表结构迁移工具 ===")
    print("此脚本将修复alerts表结构以匹配SQLAlchemy模型")
    
    confirm = input("是否继续？(y/N): ").lower().strip()
    if confirm in ['y', 'yes']:
        success = migrate_alerts_table()
        if success:
            print("\n迁移完成！现在可以重启后端服务。")
        else:
            print("\n迁移失败！请检查错误信息。")
    else:
        print("迁移已取消。")