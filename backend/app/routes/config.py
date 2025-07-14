from flask import Blueprint, request, jsonify
import numpy as np

from app.services import system_state
from app.services.danger_zone import (
    DANGER_ZONE, SAFETY_DISTANCE, LOITERING_THRESHOLD,
    save_danger_zone_config
)

# 创建配置蓝图
config_bp = Blueprint('config', __name__, url_prefix='/api')

# 危险区域编辑模式标志
edit_mode = False

@config_bp.route("/config", methods=["GET"])
def get_config():
    """获取配置信息端点
    ---
    tags:
      - 配置管理
    responses:
      200:
        description: 返回当前系统配置.
        schema:
          type: object
          properties:
            danger_zone:
              type: array
              items:
                type: array
                items:
                  type: integer
              description: 危险区域的多边形顶点坐标.
            safety_distance:
              type: integer
              description: 安全距离阈值.
            loitering_threshold:
              type: number
              description: 停留时间警报阈值.
    """
    return jsonify({
        "danger_zone": DANGER_ZONE.tolist(),
        "safety_distance": SAFETY_DISTANCE,
        "loitering_threshold": LOITERING_THRESHOLD
    })

@config_bp.route("/update_danger_zone", methods=["POST"])
def update_danger_zone():
    """更新危险区域坐标端点
    ---
    tags:
      - 配置管理
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            danger_zone:
              type: array
              items:
                type: array
                items:
                  type: integer
              description: "危险区域的新坐标点列表. e.g., [[100, 100], [200, 100], [200, 200], [100, 200]]"
    responses:
      200:
        description: 危险区域更新成功.
      400:
        description: 无效的坐标数据.
    """
    global DANGER_ZONE
    data = request.json
    new_zone = data.get('danger_zone')
    
    if new_zone and len(new_zone) >= 3:  # 确保至少有3个点形成多边形
        DANGER_ZONE = np.array(new_zone, np.int32)
        # 保存到配置文件
        if save_danger_zone_config(DANGER_ZONE, SAFETY_DISTANCE, LOITERING_THRESHOLD):
            return jsonify({"status": "success", "message": "Danger zone updated and saved successfully"})
        else:
            return jsonify({"status": "warning", "message": "Danger zone updated but failed to save to file"})
    else:
        return jsonify({"status": "error", "message": "Invalid danger zone coordinates"}), 400

@config_bp.route("/update_thresholds", methods=["POST"])
def update_thresholds():
    """更新安全距离和停留时间阈值端点
    ---
    tags:
      - 配置管理
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            safety_distance:
              type: integer
              description: 新的安全距离.
            loitering_threshold:
              type: number
              description: 新的停留阈值.
    responses:
      200:
        description: 阈值更新成功.
      400:
        description: 无效的输入值.
    """
    global SAFETY_DISTANCE, LOITERING_THRESHOLD
    data = request.json
    
    safety_distance = data.get('safety_distance')
    loitering_threshold = data.get('loitering_threshold')
    
    if safety_distance is not None:
        try:
            SAFETY_DISTANCE = int(safety_distance)
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid safety distance value"}), 400
            
    if loitering_threshold is not None:
        try:
            LOITERING_THRESHOLD = float(loitering_threshold)
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid loitering threshold value"}), 400
    
    # 保存到配置文件
    if save_danger_zone_config(DANGER_ZONE, SAFETY_DISTANCE, LOITERING_THRESHOLD):
        return jsonify({
            "status": "success", 
            "message": "Thresholds updated and saved successfully",
            "safety_distance": SAFETY_DISTANCE,
            "loitering_threshold": LOITERING_THRESHOLD
        })
    else:
        return jsonify({
            "status": "warning", 
            "message": "Thresholds updated but failed to save to file",
            "safety_distance": SAFETY_DISTANCE,
            "loitering_threshold": LOITERING_THRESHOLD
        })

@config_bp.route("/toggle_edit_mode", methods=["POST"])
def toggle_edit_mode():
    """切换危险区域编辑模式端点
    ---
    tags:
      - 配置管理
    description: >
      开启或关闭危险区域的编辑模式。
      开启后，实时视频流 (`/api/video_feed`) 可能会叠加可编辑的UI元素。
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            edit_mode:
              type: boolean
              description: true为开启编辑模式, false为关闭.
    responses:
      200:
        description: 成功切换模式.
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            edit_mode:
              type: boolean
    """
    global edit_mode
    data = request.json
    edit_mode = data.get('edit_mode', False)
    return jsonify({"status": "success", "edit_mode": edit_mode}) 

@config_bp.route("/detection_mode", methods=["GET", "POST"])
def detection_mode():
    """获取或设置检测模式
    ---
    tags:
        - 配置管理
    description: >
        GET: 获取当前的检测模式.
        POST: 设置新的检测模式。
    parameters:
      - name: body
        in: body
        required: false
        schema:
            type: object
            properties:
                mode:
                    type: string
                    enum: ['object_detection', 'face_only', 'fall_detection', 'smoking_detection']
                    description: 要设置的新模式。
    responses:
        200:
            description: 成功获取或设置模式。
        400:
            description: 无效的模式值。
    """
    if request.method == "POST":
        data = request.json
        mode = data.get('mode')
        if mode in ['object_detection', 'face_only', 'fall_detection', 'smoking_detection']:
            system_state.DETECTION_MODE = mode
            print(f"检测模式已切换为: {system_state.DETECTION_MODE}")
            return jsonify({"status": "success", "message": f"Detection mode set to {mode}"})
        return jsonify({"status": "error", "message": "Invalid mode"}), 400
    else:  # GET
        return jsonify({"mode": system_state.DETECTION_MODE}) 