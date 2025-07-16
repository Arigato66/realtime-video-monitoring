# 实时视频监控系统

本系统是一个基于YOLOv8、Flask和Vue的全栈实时视频监控应用，旨在提供一个灵活、可扩展的框架，用于集成各种计算机视觉任务，如危险区域入侵检测、人脸识别、异常行为分析等。

## 目录
- [环境配置指南](#环境配置指南)
- [项目启动](#项目启动)
- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [API端点（简要）](#api端点简要)
- [常见问题](#常见问题)

---

## 环境配置指南

为了确保项目顺利运行，请遵循以下步骤配置您的开发环境。推荐使用 [Anaconda](https://www.anaconda.com/products/distribution) 来管理Python环境。

### 1. 克隆项目

```bash
git clone [你的项目Git仓库地址]
cd realtime-video-monitoring
```

### 2. 配置后端环境 (Python)

项目后端依赖于特定的Python包，尤其是`dlib`在Windows上直接使用`pip`安装可能会失败。我们强烈建议使用`conda`来创建和管理环境。

**第一步：创建并激活Conda环境**
打开Anaconda Prompt或您的终端，使用以下命令创建一个名为 `video_monitor` 的Python 3.9环境。

```bash
conda create -n video_monitor python=3.9 -y
conda activate video_monitor
```

**第二步：安装 `dlib` (关键步骤)**
`dlib` 是 `face-recognition` 库的核心依赖，且编译过程复杂。请务必使用`conda`从`conda-forge`渠道安装预编译好的版本，以避免错误。

```bash
conda install -c https://conda.anaconda.org/conda-forge dlib
conda install -c conda-forge dlib -y
```

**第三步：安装其余Python依赖**
当`dlib`安装成功后，再使用`pip`安装`requirements.txt`中剩余的依赖包。

```bash
pip install -r requirements.txt
```

**第四步：配置 DeepFace 模型（重要）**
系统使用 DeepFace 库进行高精度人脸识别，需要下载两个关键模型文件。首次运行时会自动下载，但可能因网络问题失败。您可以手动配置：
安装deepface 0.0.93

1. 创建模型存储目录：
```bash
mkdir -p data/.deepface_models/.deepface/weights
```

2. 下载必要的模型文件（两个文件总计约256MB）：
   - [arcface_weights.h5](https://github.com/serengil/deepface_models/releases/download/v1.0/arcface_weights.h5) (137MB) - 用于人脸特征提取和比对
   - [retinaface.h5](https://github.com/serengil/deepface_models/releases/download/v1.0/retinaface.h5) (119MB) - 用于人脸检测

3. 将下载的文件放入 `data/.deepface_models/.deepface/weights/` 目录

4. 验证模型文件是否正确放置：
```bash
# Windows
dir data\.deepface_models\.deepface\weights

# Linux/Mac
ls -la data/.deepface_models/.deepface/weights
```

应该能看到两个模型文件 `arcface_weights.h5` 和 `retinaface.h5`。

**第五步：配置人脸识别数据存储**

系统需要以下目录结构来存储和管理人脸数据：

```
data/
├── .deepface_models/        # DeepFace模型存储目录
│   └── .deepface/
│       └── weights/
│           ├── arcface_weights.h5
│           └── retinaface.h5
│
├── registered_faces/        # 注册人脸图像存储目录
│   ├── person1_name/        # 每个注册人员一个文件夹（文件夹名为人员姓名）
│   │   ├── uuid1.jpg        # 该人员的人脸图像（可以有多张）
│   │   └── uuid2.jpg
│   │
│   └── person2_name/
│       └── uuid3.jpg
│
└── representations_arcface.pkl  # DeepFace生成的人脸特征索引文件（自动生成）
```

确保 `data` 目录存在并可写：

```bash
mkdir -p data/registered_faces
```


### 3. 配置前端环境 (Node.js)

项目前端是基于Vue.js和Vite构建的。请确保您已安装 [Node.js](https://nodejs.org/) (推荐LTS版本)。

进入前端项目目录，安装npm依赖。

```bash
cd frontend/realtime-monitor-fronted
npm install
```

---

## 项目启动

你需要打开两个终端来分别启动后端和前端服务。

#### 启动后端

```bash
conda activate video_monitor
cd backend
python run.py
```
后端服务将运行在 `http://localhost:5000`。

#### 启动前端

```bash
cd frontend/realtime-monitor-fronted
npm run dev
```
服务启动后，在浏览器中打开前端地址 (通常是 `http://localhost:5173`) 即可访问系统。

---

## 功能特性

- **实时视频处理**: 支持通过本地摄像头或上传视频文件进行分析。
- **通用目标检测**: 基于YOLOv8，可识别多种常见物体。
- **自定义危险区域**: 用户可通过前端交互界面，动态设置和调整多边形危险区域。
- **智能告警系统**:
    - **入侵告警**: 当人员进入危险区域时触发。
    - **接近告警**: 当人员与危险区域边缘小于设定的安全距离时触发。
    - **徘徊告警**: 当人员在危险区域内停留时间超过设定的阈值时触发。
- **人脸识别与管理**:
    - 支持注册、删除人脸信息。
    - 在视频中识别已注册人员，并标记陌生人。
    - 陌生人闯入时自动生成告警。
    - **多线程优化**: 使用线程池异步处理人脸识别任务，避免视频流卡顿。
    - **结果稳定性**: 实现"结果黏滞"机制，连续多次识别失败才将人标记为陌生人。
    - **图像质量控制**: 基于Laplacian算子的图像清晰度评估，只处理清晰的人脸图像。
    - **强制识别机制**: 即使图像不够清晰，也会定期尝试识别，避免长时间显示"Identifying..."。
- **动态参数配置**: 安全距离、停留阈值等核心参数均可在前端动态调整。

### 人脸识别技术细节

本系统采用了先进的人脸识别技术栈，结合了多种模型和算法：

1. **人脸检测与追踪**:
   - 使用YOLOv8-face模型进行高效的人脸检测
   - 实现目标追踪，为每个检测到的人脸分配唯一ID
   - 模型文件: `yolov8n-face-lindevs.pt`

2. **人脸识别**:
   - 基于DeepFace库，使用ArcFace模型进行高精度人脸特征提取
   - 采用余弦距离(cosine distance)进行人脸相似度比较
   - 模型文件: `arcface_weights.h5`

3. **人脸注册流程**:
   - 上传人脸图像 → 使用RetinaFace检测人脸 → 存储图像 → 更新特征索引
   - 每个注册人员在 `data/registered_faces/{name}/` 目录下可存储多张照片
   - 模型文件: `retinaface.h5`

4. **识别优化技术**:
   - **图像质量评估**: 使用Laplacian算子计算图像清晰度，过滤模糊图像
   - **异步处理**: 使用ThreadPoolExecutor实现非阻塞的人脸识别
   - **结果稳定性**: 需要连续多次识别失败才会将人标记为陌生人
   - **定期强制识别**: 即使图像质量不佳，也会定期尝试识别

5. **数据管理**:
   - 使用MySQL数据库存储人员基本信息
   - 使用文件系统存储人脸图像
   - 特征向量通过DeepFace自动管理和索引

---

## 技术栈

| 类别       | 技术                               |
| :--------- | :--------------------------------- |
| **前端**   | Vue 3, Vite, Pinia, Vue Router     |
| **后端**   | Flask, Flask-CORS                  |
| **AI/CV**  | YOLOv8 (Ultralytics), OpenCV, `face_recognition`, NumPy |
| **数据库** | JSON (用于人脸特征和配置存储)      |

---

## 项目结构
```
realtime-video-monitoring/
│
├── backend/                # Flask后端
│   ├── app/                # 应用核心模块
│   │   ├── routes/         # API路由
│   │   ├── services/       # 业务逻辑服务
│   │   └── utils/          # 工具函数
│   ├── run.py              # 应用入口
│   └── ...
│
├── frontend/               # Vue前端
│   └── realtime-monitor-fronted/
│       ├── src/            # 源代码
│       │   ├── views/      # 页面视图 (如MonitorView.vue)
│       │   ├── components/ # 可复用组件
│       │   └── ...
│       └── ...
│
├── data/                   # 数据存储目录
│   └── face_encodings.json # 持久化的人脸特征数据
│
├── danger_zone_config.json # 危险区域配置文件
├── requirements.txt        # Python依赖
└── README.md               # 本文档
```

---

## API端点（简要）

- `GET /api/status`: 检查后端服务状态。
- `POST /api/upload`: 上传视频/图片进行分析。
- `GET /api/video_feed`: 获取实时摄像头处理流。
- `GET /api/config`: 获取危险区域和阈值配置。
- `POST /api/update_danger_zone`: 更新危险区域。
- `POST /api/update_thresholds`: 更新告警阈值。
- `GET /api/faces`: 获取已注册人脸列表。
- `POST /api/faces/register`: 注册新人脸。
- `DELETE /api/faces/<name>`: 删除人脸。

---

## 常见问题

1. **摄像头无法打开?**
   - 确保摄像头驱动正常，且没有被其他程序（如腾讯会议、钉钉）占用。
   - 检查浏览器是否已授予网页摄像头访问权限。

2. **人脸识别不准确?**
   - 确保用于注册的照片是清晰、无遮挡的正面照。
   - 识别时的光线、角度和面部遮挡（如戴口罩）会影响识别成功率。
   - 如果识别结果一直显示"Identifying..."，可能是因为图像清晰度不足。尝试在更好的光线条件下重新测试。

3. **依赖安装失败?**
   - **后端**: 严格遵循环境配置指南，特别是使用`conda`安装`dlib`的步骤。
   - **前端**: 如果`npm install`失败，尝试删除`node_modules`文件夹和`package-lock.json`文件后，再重新运行`npm install`。

4. **DeepFace模型问题?**
   - **模型下载失败**: 如果首次运行时自动下载模型失败，请按照环境配置指南中的第四步手动下载并放置模型文件。
   - **识别速度慢**: 首次使用时系统需要加载模型，可能会有短暂延迟。后续使用会更流畅。
   - **内存不足错误**: DeepFace模型较大，确保您的系统有足够的RAM（建议至少8GB）。

5. **性能问题?**
   - 人脸识别和目标检测是计算密集型任务。在配置较低的机器上，实时处理的帧率可能会下降。
   - 考虑在后续开发中增加一个“性能模式”，例如通过降低检测频率或分辨率来提升流畅度。


暴力检测模块启动方式（暂时）：
cd backend/app/services
python violenceDetect.py --camera --model vd.hdf5

---

## 高级配置

### DeepFace 人脸识别参数调整

如果您需要调整人脸识别的敏感度或性能，可以修改以下关键参数：

1. **识别阈值调整**：
   打开 `backend/app/services/face_service.py` 文件，找到并修改以下参数：
   ```python
   # 为ArcFace模型设置的识别阈值，低于此值表示匹配
   RECOGNITION_THRESHOLD = 0.68  # 默认值
   ```
   - 降低此值（如改为0.5）会增加识别严格度，减少误识别，但可能导致已注册用户被识别为陌生人
   - 提高此值（如改为0.85）会增加识别容忍度，提高已注册用户的识别率，但可能增加误识别风险

2. **图像清晰度阈值调整**：
   打开 `backend/app/services/detection.py` 文件，在 `process_faces_only` 函数中找到：
   ```python
   BLUR_THRESHOLD = 25.0  # 清晰度阈值，低于此值的图像被视为模糊
   ```
   - 降低此值会处理更多模糊图像，可能提高识别频率，但准确率可能下降
   - 提高此值会过滤掉更多模糊图像，提高识别准确率，但可能导致识别频率降低

3. **强制识别时间调整**：
   同样在 `process_faces_only` 函数中：
   ```python
   FORCE_RECOGNITION_TIME = 3.0  # 即使图像模糊，也至少每3秒尝试一次识别
   ```
   - 降低此值会更频繁地尝试识别模糊图像，可能减少"Identifying..."状态的持续时间
   - 提高此值可以减少对模糊图像的处理，节省计算资源

4. **连续未识别阈值调整**：
   ```python
   UNKNOWN_CONFIDENCE_THRESHOLD = 5  # 连续5次识别为陌生人才确认
   ```
   - 降低此值会更快地将人标记为"Stranger"，但可能导致已注册用户被错误标记
   - 提高此值会增加系统的容忍度，减少误标记，但可能导致陌生人被标记为"Identifying..."的时间延长

5. **识别间隔调整**：
   ```python
   RECOGNITION_INTERVAL = 0.5  # 每0.5秒尝试识别一次
   ```
   - 降低此值会增加识别频率，可能提高响应速度，但会增加系统负载
   - 提高此值会减少识别频率，降低系统负载，但可能导致响应延迟

这些参数可以根据您的具体使用环境和需求进行调整，以达到最佳的识别效果和性能平衡。