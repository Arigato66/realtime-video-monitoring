class ConfigService:
    """
    一个简单的服务，用于在内存中管理应用程序的全局状态。
    目前主要用于跟踪当前的检测模式。
    """
    _instance = None
    _detection_mode = 'face_only'  # 默认模式

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigService, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_detection_mode(cls):
        """获取当前的检测模式"""
        return cls._detection_mode

    @classmethod
    def set_detection_mode(cls, mode):
        """设置新的检测模式"""
        # 可以添加验证，确保模式是有效的
        valid_modes = ['face_only', 'object_detection', 'fall_detection', 'smoking_detection', 'violence_detection']
        if mode in valid_modes:
            cls._detection_mode = mode
            return True
        return False