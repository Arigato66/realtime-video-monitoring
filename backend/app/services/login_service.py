import uuid
import mysql.connector
from werkzeug.security import check_password_hash
from app.config import Config

class LoginService:
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

    def get_user_by_username(self, username):
        """根据用户名获取用户（核心查询方法）"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            # 关键：查询条件为username字段
            cursor.execute(
                "SELECT * FROM users WHERE username = %s",
                (username,)
            )
            return cursor.fetchone()  # 返回用户数据或None
        except mysql.connector.Error as err:
            print(f"查询用户失败: {err}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    def verify_user(self, username, password):
        """验证用户（添加测试输出）"""
        try:
            # 1. 打印接收到的用户名（密码只打印长度，避免明文泄露）
            print(f"\n===== 开始验证用户 =====")
            print(f"接收到的用户名：{username}")
            print(f"接收到的密码长度：{len(password)}（仅显示长度，避免明文）")

            # 2. 查询用户时打印查询条件
            print(f"开始查询用户：{username}")
            user = self.get_user_by_username(username)
            
            if not user:
                print(f"验证结果：用户名不存在（{username}）")
                return False, "用户名不存在"
            
            # 3. 密码验证时打印结果（不打印具体密码）
            password_match = check_password_hash(user['password'], password)
            print(f"密码验证结果：{'成功' if password_match else '失败'}")
            if not password_match:
                return False, "密码错误"
            
            # 4. 账户激活状态检查
            print(f"账户激活状态：{'已激活' if user.get('is_active', True) else '未激活'}")
            if not user.get('is_active', True):
                return False, "账户未激活，请先激活"
            
            # 5. 验证成功时打印用户ID
            print(f"验证成功！用户ID：{user['user_id']}")
            self.update_login_time(user['user_id'])
            
            return True, user
        except Exception as e:
            print(f"验证异常：{e}，当前用户名：{username}")
            return False, "服务器内部错误"

    def update_login_time(self, user_id):
        """更新用户最后登录时间"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = %s",
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

    # 移除get_user_by_email方法（如果不需要邮箱登录）