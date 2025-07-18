from app import db
from app.models.system_log import SystemLog
import traceback
import logging

# 配置基本日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def log_to_db(level, module, message, details=None, user_id=None):
    """
    记录日志到数据库
    
    参数:
        level: 日志级别 (INFO/WARNING/ERROR/CRITICAL)
        module: 模块名称
        message: 日志消息
        details: 详细信息 (可选)
        user_id: 操作用户ID (可选)
    
    返回:
        SystemLog: 创建的日志对象
    """
    try:
        # 创建日志记录
        log_entry = SystemLog(
            log_level=level,
            module=module,
            message=message,
            details=details,
            user_id=user_id
        )
        
        # 保存到数据库
        db.session.add(log_entry)
        db.session.commit()
        
        return log_entry
    except Exception as e:
        db.session.rollback()
        logger.error(f"记录日志到数据库失败: {e}")
        logger.error(traceback.format_exc())
        return None

def log_with_app_context(level, module, message, details=None, user_id=None):
    """
    使用应用上下文记录日志到数据库
    
    参数:
        level: 日志级别 (INFO/WARNING/ERROR/CRITICAL)
        module: 模块名称
        message: 日志消息
        details: 详细信息 (可选)
        user_id: 操作用户ID (可选)
    
    返回:
        SystemLog: 创建的日志对象
    """
    try:
        # 导入应用并创建上下文
        from app import create_app
        app = create_app()
        with app.app_context():
            return log_to_db(level, module, message, details, user_id)
    except Exception as e:
        logger.error(f"创建应用上下文失败: {e}")
        logger.error(traceback.format_exc())
        # 记录到标准日志
        logger.log(
            logging.INFO if level == "INFO" else
            logging.WARNING if level == "WARNING" else
            logging.ERROR if level == "ERROR" else
            logging.CRITICAL,
            f"[{module}] {message} - {details if details else ''}"
        )
        return None

def log_info(module, message, details=None, user_id=None):
    """记录INFO级别日志"""
    # 记录到标准日志
    logger.info(f"[{module}] {message}")
    # 尝试记录到数据库，使用应用上下文
    return log_with_app_context("INFO", module, message, details, user_id)

def log_warning(module, message, details=None, user_id=None):
    """记录WARNING级别日志"""
    # 记录到标准日志
    logger.warning(f"[{module}] {message}")
    # 尝试记录到数据库，使用应用上下文
    return log_with_app_context("WARNING", module, message, details, user_id)

def log_error(module, message, details=None, user_id=None):
    """记录ERROR级别日志"""
    # 记录到标准日志
    logger.error(f"[{module}] {message}")
    # 尝试记录到数据库，使用应用上下文
    return log_with_app_context("ERROR", module, message, details, user_id)

def log_critical(module, message, details=None, user_id=None):
    """记录CRITICAL级别日志"""
    # 记录到标准日志
    logger.critical(f"[{module}] {message}")
    # 尝试记录到数据库，使用应用上下文
    return log_with_app_context("CRITICAL", module, message, details, user_id)

def get_logs(page=1, per_page=20, level=None, module=None, start_date=None, end_date=None):
    """
    获取系统日志，支持分页和过滤
    
    参数:
        page: 页码
        per_page: 每页数量
        level: 日志级别过滤
        module: 模块名称过滤
        start_date: 开始日期
        end_date: 结束日期
    
    返回:
        分页的日志列表
    """
    query = SystemLog.query
    
    # 应用过滤条件
    if level:
        query = query.filter(SystemLog.log_level == level)
    if module:
        query = query.filter(SystemLog.module == module)
    if start_date:
        query = query.filter(SystemLog.log_time >= start_date)
    if end_date:
        query = query.filter(SystemLog.log_time <= end_date)
    
    # 按时间降序排列
    query = query.order_by(SystemLog.log_time.desc())
    
    # 返回分页结果
    return query.paginate(page=page, per_page=per_page, error_out=False) 