import uuid
import mysql.connector
from werkzeug.security import generate_password_hash
from app.config import Config

class RegisterService:
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

    def username_exists(self, username):
        """检查用户名是否已存在"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT user_id FROM users WHERE username = %s",
                (username,)
            )
            return cursor.fetchone() is not None
        except mysql.connector.Error as err:
            print(f"检查用户名失败: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def email_exists(self, email):
        """检查邮箱是否已存在"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT user_id FROM users WHERE email = %s",
                (email,)
            )
            return cursor.fetchone() is not None
        except mysql.connector.Error as err:
            print(f"检查邮箱失败: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def create_user(self, username, email, password):
        """创建新用户（与users表结构完全匹配）"""
        # 检查用户名和邮箱是否已存在
        if self.username_exists(username):
            return False, "用户名已存在"
        if self.email_exists(email):
            return False, "邮箱已存在"
            
        # 生成UUID作为用户唯一标识
        user_id = str(uuid.uuid4())
        # 对密码进行哈希处理（安全存储）
        hashed_password = generate_password_hash(password)
        
        # -------------------- 测试信息输出 --------------------
        print("\n===== 即将存入数据库的用户记录 =====")
        print(f"user_id: {user_id}")
        print(f"username: {username}")
        print(f"email: {email}")
        print(f"hashed_password (长度: {len(hashed_password)}): {hashed_password[:50]}...")  # 只显示前50字符
        print(f"created_at: CURRENT_TIMESTAMP")
        print(f"last_login: CURRENT_TIMESTAMP")
        print(f"is_active: 0")
        print("===================================\n")
        # -----------------------------------------------------

        # 连接数据库并执行插入操作
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # SQL语句字段与表结构严格对应（顺序可调整，但值必须一一对应）
            cursor.execute(
                """
                INSERT INTO users (
                    user_id, 
                    username, 
                    password, 
                    email, 
                    created_at, 
                    last_login, 
                    is_active
                ) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                """,
                # 注意：参数顺序必须与SQL字段顺序一致
                (user_id, username, hashed_password, email)
            )
            conn.commit()  # 提交事务
            return True, user_id  # 返回成功状态和用户ID
        except mysql.connector.Error as err:
            print(f"创建用户失败: {err}")
            conn.rollback()  # 出错时回滚事务
            return False, str(err)  # 返回失败状态和错误信息
        finally:
            # 确保资源释放
            cursor.close()
            conn.close()