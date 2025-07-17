import uuid
import os
from werkzeug.security import check_password_hash
from app.config import config

class LoginService:
    def __init__(self):
        # 根据当前环境获取配置
        env = os.environ.get('FLASK_CONFIG', 'development')
        self.current_config = config[env]()
        self.is_mysql = hasattr(self.current_config, 'MYSQL_HOST')
        
        if self.is_mysql:
            # MySQL配置
            import mysql.connector
            self.mysql_config = {
                'host': self.current_config.MYSQL_HOST,
                'port': self.current_config.MYSQL_PORT,
                'user': self.current_config.MYSQL_USER,
                'password': self.current_config.MYSQL_PASSWORD,
                'database': self.current_config.MYSQL_DB,
                'charset': self.current_config.MYSQL_CHARSET
            }
        else:
            # SQLite配置
            import sqlite3
            self.sqlite_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'app.db'
            )

    def get_connection(self):
        if self.is_mysql:
            import mysql.connector
            return mysql.connector.connect(**self.mysql_config)
        else:
            import sqlite3
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            return conn

    def get_user_by_username(self, username):
        """根据用户名获取用户（支持MySQL和SQLite）"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            
            if self.is_mysql:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                    "SELECT * FROM users WHERE username = %s",
                    (username,)
                )
                result = cursor.fetchone()
            else:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM users WHERE username = ?",
                    (username,)
                )
                row = cursor.fetchone()
                result = dict(row) if row else None
                
            return result
        except Exception as err:
            print(f"查询用户失败: {err}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def verify_user(self, username, password):
        """验证用户（支持MySQL和SQLite）"""
        try:
            print(f"\n===== 开始验证用户 =====")
            print(f"当前环境: {'MySQL' if self.is_mysql else 'SQLite'}")
            print(f"接收到的用户名：{username}")
            print(f"接收到的密码长度：{len(password)}")

            # 查询用户
            print(f"开始查询用户：{username}")
            user = self.get_user_by_username(username)
            
            if not user:
                print(f"验证结果：用户名不存在（{username}）")
                return False, "用户名不存在"
            
            # 密码验证
            password_match = check_password_hash(user['password'], password)
            print(f"密码验证结果：{'成功' if password_match else '失败'}")
            if not password_match:
                return False, "密码错误"
            
            # 账户激活状态检查
            is_active = user.get('is_active', True)
            if isinstance(is_active, int):
                is_active = bool(is_active)
            print(f"账户激活状态：{'已激活' if is_active else '未激活'}")
            if not is_active:
                return False, "账户未激活，请先激活"
            
            # 验证成功
            print(f"验证成功！用户ID：{user['user_id']}")
            self.update_login_time(user['user_id'])
            
            return True, user
        except Exception as e:
            print(f"验证异常：{e}，当前用户名：{username}")
            return False, "服务器内部错误"

    def update_login_time(self, user_id):
        """更新用户最后登录时间（支持MySQL和SQLite）"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.is_mysql:
                cursor.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = %s",
                    (user_id,)
                )
            else:
                cursor.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (user_id,)
                )
            
            conn.commit()
            return True
        except Exception as err:
            print(f"更新登录时间失败: {err}")
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()