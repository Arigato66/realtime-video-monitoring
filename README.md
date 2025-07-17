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
- **动态参数配置**: 安全距离、停留阈值等核心参数均可在前端动态调整。

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

3. **依赖安装失败?**
   - **后端**: 严格遵循环境配置指南，特别是使用`conda`安装`dlib`的步骤。
   - **前端**: 如果`npm install`失败，尝试删除`node_modules`文件夹和`package-lock.json`文件后，再重新运行`npm install`。

4. **性能问题?**
   - 人脸识别和目标检测是计算密集型任务。在配置较低的机器上，实时处理的帧率可能会下降。
   - 考虑在后续开发中增加一个“性能模式”，例如通过降低检测频率或分辨率来提升流畅度。


暴力检测模块启动方式（暂时）：
cd backend/app/services
python violenceDetect.py --camera --model vd.hdf5