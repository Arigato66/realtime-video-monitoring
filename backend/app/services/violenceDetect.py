import os
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications import VGG16
from tensorflow.keras.models import Model
import time
from collections import deque
from tensorflow.keras import initializers  # 新增导入
import threading  # 新增导入

# 增强初始化器映射，解决序列化标识符识别问题
CUSTOM_OBJECTS = {
    'Orthogonal': initializers.Orthogonal,
    'keras.initializers.Orthogonal': initializers.Orthogonal,
    'OrthogonalV2': initializers.Orthogonal,
    'keras.initializers.OrthogonalV2': initializers.Orthogonal
}

# 新增模型加载函数，统一加载逻辑
def load_model_safely(model_path):
    """safe加载模型，处理初始化器兼容性问题"""
    try:
        model = tf.keras.models.load_model(
            model_path, 
            compile=False,
            custom_objects=CUSTOM_OBJECTS
        )
        model.trainable = False
        return model
    except Exception as e:
        print(f"加载模型失败: {e}")
        print("请检查模型文件路径和TensorFlow版本兼容性")
        raise


def predict_video(video_path, model_path='vd.hdf5', vgg_weights_path=None):
    """
    使用训练好的模型预测视频是否包含violence行为
    
    参数:
        video_path: 视频文件路径
        model_path: 训练好的模型路径 (默认vd.hdf5)
        vgg_weights_path: VGG16权重文件路径 (可选)
    """
    # 使用统一的safe加载函数
    model = load_model_safely(model_path)
    
    # 加载VGG16特征提取器
    if vgg_weights_path:
        # 使用本地权重
        vgg_model = VGG16(include_top=True, weights=None)
        vgg_model.load_weights(vgg_weights_path)
    else:
        # 尝试自动下载
        try:
            vgg_model = VGG16(include_top=True, weights='imagenet')
        except Exception as e:
            print("自动下载VGG16权重失败，请手动下载并指定路径")
            print("下载地址: https://storage.googleapis.com/tensorflow/keras-applications/vgg16/vgg16_weights_tf_dim_ordering_tf_kernels.h5")
            raise
    
    transfer_layer = vgg_model.get_layer('fc2')
    image_model_transfer = Model(inputs=vgg_model.input, outputs=transfer_layer.output)
    
    # 处理视频帧
    frames = get_frames(video_path)
    
    # 提取特征
    transfer_values = image_model_transfer.predict(frames)
    
    # 预测
    prediction = model.predict(np.array([transfer_values]))
    
    # 返回结果
    violence_prob = prediction[0][0]
    non_violence_prob = prediction[0][1]
    return violence_prob, non_violence_prob

def get_frames(video_path, images_per_file=20, img_size=224):
    """
    从视频中提取帧
    
    参数:
        video_path: 视频文件路径
        images_per_file: 提取的帧数 (默认20)
        img_size: 帧尺寸 (默认224)
    
    返回:
        处理后的帧数组
    """
    images = []
    vidcap = cv2.VideoCapture(video_path)
    success, image = vidcap.read()
    count = 0

    while count < images_per_file and success:
        RGB_img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        res = cv2.resize(RGB_img, dsize=(img_size, img_size), interpolation=cv2.INTER_CUBIC)
        images.append(res)
        success, image = vidcap.read()
        count += 1

    # 如果视频帧不足，用最后一帧填充
    while len(images) < images_per_file:
        images.append(images[-1].copy() if images else np.zeros((img_size, img_size, 3)))
    
    ret = np.array(images)
    return (ret / 255.).astype(np.float32)

# ===================== 新版异步推理实时监控 =====================
def real_time_monitoring(model, image_model_transfer, camera_index=0, interval=2.0, frame_skip=4):
    print("="*50)
    print("GPU配置验证:")
    print("物理GPU设备:", tf.config.list_physical_devices('GPU'))
    try:
        build_info = tf.sysconfig.get_build_info()
        print(f"CUDA版本: {build_info.get('cuda_version', '未知')}")
        print(f"cuDNN版本: {build_info.get('cudnn_version', '未知')}")
    except AttributeError:
        print("无法获取CUDA/cuDNN版本信息")
    print("="*50)

    buffer = deque(maxlen=600)  # 20秒缓冲
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"无法打开摄像头 {camera_index}")
        return

    print("开始实时监控，按 'q' 键退出...")
    frame_counter = 0
    running = True

    # 用于线程safe地存储推理结果
    result_lock = threading.Lock()
    latest_result = {"status": "unknown", "violence_prob": 0.0}

    def inference_worker():
        while running:
            if len(buffer) >= 20:
                frames_to_analyze = list(buffer)[-20:]
                try:
                    transfer_values = image_model_transfer.predict(np.array(frames_to_analyze), verbose=0)
                    prediction = model.predict(np.array([transfer_values]), verbose=0)
                    violence_prob = float(prediction[0][0])
                    # state判断
                    if violence_prob <= 0.5:
                        status = "safe"
                    elif violence_prob <= 0.7:
                        status = "caution"
                    else:
                        status = "warning"
                    with result_lock:
                        latest_result["status"] = status
                        latest_result["violence_prob"] = violence_prob
                    # 终端输出
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{timestamp}] state: {status}, violenceProbability: {violence_prob:.4f}")
                except Exception as e:
                    print(f"推理线程异常: {e}")
            time.sleep(interval)

    # 启动推理线程
    infer_thread = threading.Thread(target=inference_worker, daemon=True)
    infer_thread.start()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("读取摄像头帧失败")
                break
            processed_frame = process_frame(frame)
            buffer.append(processed_frame)
            frame_counter += 1

            # 画面显示最新推理结果
            display_frame = frame.copy()
            with result_lock:
                status = latest_result["status"]
                violence_prob = latest_result["violence_prob"]
            color = (0, 255, 0) if status == "safe" else (0, 255, 255) if status == "caution" else (0, 0, 255)
            cv2.putText(display_frame, f"state: {status}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(display_frame, f"violenceProbability: {violence_prob:.4f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.imshow('实时监控', display_frame)
            # 按q键退出
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        running = False
        cap.release()
        cv2.destroyAllWindows()
        print("监控已结束")

# ===================== END =====================

def process_frame(frame, img_size=224):
    """处理单帧图像"""
    RGB_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = cv2.resize(RGB_img, dsize=(img_size, img_size), interpolation=cv2.INTER_CUBIC)
    return (res / 255.).astype(np.float32)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='violence行为检测推理')
    parser.add_argument('--video', type=str, help='要检测的视频文件路径')
    parser.add_argument('--camera', action='store_true', help='启用摄像头实时监控')
    parser.add_argument('--model', type=str, default='vd.hdf5', help='模型文件路径 (默认vd.hdf5)')
    parser.add_argument('--vgg_weights', type=str, default=None, help='VGG16权重文件路径 (可选)')
    parser.add_argument('--interval', type=float, default=2.0, help='实时监控分析间隔(秒)')
    parser.add_argument('--frame_skip', type=int, default=4, help='抽帧比例(每n帧处理1帧)')
    args = parser.parse_args()

    # 参数验证
    if not args.video and not args.camera:
        parser.error("必须指定 --video 或 --camera 参数")
    
    # 使用统一的safe加载函数
    model = load_model_safely(args.model)
    
    if args.vgg_weights:
        vgg_model = VGG16(include_top=True, weights=None)
        vgg_model.load_weights(args.vgg_weights)
    else:
        try:
            vgg_model = VGG16(include_top=True, weights='imagenet')
        except Exception as e:
            print("自动下载VGG16权重失败，请手动下载并指定路径")
            print("下载地址: https://storage.googleapis.com/tensorflow/keras-applications/vgg16/vgg16_weights_tf_dim_ordering_tf_kernels.h5")
            raise
    
    transfer_layer = vgg_model.get_layer('fc2')
    image_model_transfer = Model(inputs=vgg_model.input, outputs=transfer_layer.output)
    
    # 根据参数选择执行模式
    if args.camera:
        real_time_monitoring(
            model, 
            image_model_transfer, 
            interval=args.interval,
            frame_skip=args.frame_skip
        )
    elif args.video:
        violence_prob, non_violence_prob = predict_video(
            args.video, 
            model_path=args.model,
            vgg_weights_path=args.vgg_weights
        )
        
        print("\n检测结果:")
        print(f"violenceProbability: {violence_prob:.4f}")
        print(f"非violenceProbability: {non_violence_prob:.4f}")
        
        if violence_prob > 0.7:
            print("warning: 检测到高Probabilityviolence行为!")
        elif violence_prob > 0.5:
            print("caution: 检测到可能的violence行为")
        else:
            print("safe: 未检测到明显violence行为")