import uuid
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from app.config import Config

class DBService:
    def __init__(self):
        self.config = {
            'host': Config.MYSQL_HOST,
            'port': Config.MYSQL_PORT,
            'user': Config.MYSQL_USER,
            'password': Config.MYSQL_PASSWORD,
            'database': Config.MYSQL_DB,
            'charset': Config.MYSQL_CHARSET
        }

    def get_connection(self):
        return mysql.connector.connect(**self.config)

    # 用户操作方法
    def create_user(self, username, password, email):
        """创建新用户"""
        user_id = str(uuid.uuid4())
        hashed_password = generate_password_hash(password)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (user_id, username, password, email) "
                "VALUES (%s, %s, %s, %s)",
                (user_id, username, hashed_password, email)
            )
            conn.commit()
            return user_id
        except mysql.connector.Error as err:
            print(f"创建用户失败: {err}")
            return None
        finally:
            cursor.close()
            conn.close()

    def get_user_by_username(self, username):
        """根据用户名获取用户"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM users WHERE username = %s",
                (username,)
            )
            return cursor.fetchone()
        except mysql.connector.Error as err:
            print(f"查询用户失败: {err}")
            return None
        finally:
            cursor.close()
            conn.close()

    def get_user_by_email(self, email):
        """根据邮箱获取用户"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM users WHERE email = %s",
                (email,)
            )
            return cursor.fetchone()
        except mysql.connector.Error as err:
            print(f"查询用户失败: {err}")
            return None
        finally:
            cursor.close()
            conn.close()

    def verify_user(self, username, password):
        """验证用户凭据"""
        user = self.get_user_by_username(username)
        if user and check_password_hash(user['password'], password):
            return user
        return None

    def update_login_time(self, user_id):
        """更新用户最后登录时间"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP "
                "WHERE user_id = %s",
                (user_id,)
            )
            conn.commit()
            return True
        except mysql.connector.Error as err:
            print(f"更新登录时间失败: {err}")
            return False
        finally:
            cursor.close()
            conn.close()