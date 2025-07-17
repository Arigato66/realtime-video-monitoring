<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
     <TopBar />
    <header class="top-bar">
      <div class="header-left">
        <h1>车站实时视频监控系统</h1>
      </div>
      <div class="header-right">
        <div class="profile-info">
          <div class="avatar">
            <img src="https://via.placeholder.com/100" alt="用户头像">
          </div>
          <div class="name-role">
            <h2>张三</h2>
            <p>管理员</p>
          </div>
        </div>
      </div>
    </header>

    <!-- 新增：人脸注册模态框 -->
    <div v-if="showRegistrationModal" class="registration-modal-overlay">
      <div class="registration-modal-content">
        <h2>正在为 "{{ registrationName }}" 注册人脸</h2>
        <div class="registration-video-container">
          <video ref="registrationVideoEl" autoplay playsinline class="registration-video"></video>
        </div>
        <div class="registration-status">
          <p>状态: {{ registrationStatus }}</p>
          <p>已成功捕获: {{ capturedFramesCount }} 帧</p>
        </div>
        <div class="registration-controls">
          <button @click="captureFrame" class="capture-button">捕获当前帧</button>
          <button @click="closeRegistrationModal" class="finish-button">完成注册</button>
        </div>
      </div>
    </div>

    <!-- 新增：RTMP流连接模态框 -->
    <div v-if="showRtmpConnectionModal" class="rtmp-modal-overlay">
      <div class="rtmp-modal-content">
        <h2>RTMP流连接配置</h2>
        <div class="rtmp-form">
          <div class="form-group">
            <label>流名称:</label>
            <input v-model="rtmpConfig.name" type="text" placeholder="请输入流名称" class="rtmp-input" />
          </div>
          <div class="form-group">
            <label>RTMP地址:</label>
            <input v-model="rtmpConfig.rtmp_url" type="text" placeholder="rtmp://example.com/live/stream" class="rtmp-input" />
          </div>
          <div class="form-group">
            <label>描述 (可选):</label>
            <input v-model="rtmpConfig.description" type="text" placeholder="流描述信息" class="rtmp-input" />
          </div>
          <div class="form-group">
            <label>检测模式:</label>
            <div class="detection-modes">
              <label class="checkbox-label">
                <input type="checkbox" v-model="rtmpConfig.detection_modes" value="object_detection" />
                目标检测
              </label>
              <label class="checkbox-label">
                <input type="checkbox" v-model="rtmpConfig.detection_modes" value="face_only" />
                人脸识别
              </label>
              <label class="checkbox-label">
                <input type="checkbox" v-model="rtmpConfig.detection_modes" value="fall_detection" />
                跌倒检测
              </label>
              <label class="checkbox-label">
                <input type="checkbox" v-model="rtmpConfig.detection_modes" value="smoking_detection" />
                抽烟检测
              </label>
              <!-- 新增暴力检测选项 -->
              <label class="checkbox-label">
                <input type="checkbox" v-model="rtmpConfig.detection_modes" value="violence_detection" />
                暴力检测
              </label>
            </div>
          </div>
        </div>
        <div class="rtmp-controls">
          <button @click="connectRtmpStream" class="connect-button" :disabled="!rtmpConfig.name || !rtmpConfig.rtmp_url">连接流</button>
          <button @click="closeRtmpModal" class="cancel-button">取消</button>
        </div>
        <div v-if="rtmpStatus" class="rtmp-status">
          <p>{{ rtmpStatus }}</p>
        </div>
      </div>
    </div>

    <div class="main-content">
      <!-- 主内容区域 - 实时视频监控系统内容 -->
      <main class="content-area">
        <div class="monitor-page">
          <h1>实时视频监控系统</h1>
          
          <div class="monitor-container">
            <div class="video-container">
              <h2>监控视图</h2>
              <div class="video-wrapper">


                <!-- Case 1: Webcam is active -->
                <img v-if="activeSource === 'webcam'" ref="webcamImg" alt="摄像头实时画面" class="webcam-feed" />
                
                <!-- Case 2: RTMP流显示 - 使用Canvas -->
                <canvas v-else-if="activeSource === 'rtmp'" 
                        ref="rtmpCanvas" 
                        class="rtmp-canvas" 
                        :width="canvasWidth" 
                        :height="canvasHeight">
                </canvas>
                
                <!-- Case 3: Upload显示 -->
                <template v-else-if="activeSource === 'upload'">
                  <img v-if="isImageUrl(videoSource)" :src="videoSource" alt="上传的图像" />
                  <video v-else-if="isVideoUrl(videoSource)" :src="videoSource" controls autoplay></video>
                </template>

                <!-- Case 4: Loading -->
                <div v-else-if="activeSource === 'loading'" class="loading-state">
                  <p>正在处理文件，请稍候...</p>
                  <div class="loading-spinner"></div>
                </div>
                
                <!-- Case 5: Default placeholder -->
                <div v-else class="video-placeholder">
                  <p>加载中或未连接视频源</p>
                </div>

        </div>
      </div>
      
            <div class="control-panel">
              <h2>控制面板</h2>
              
              <!-- 视频源选择 -->

              <div class="control-section">
                <h3>视频源</h3>
                <div class="button-group">
                  <button @click="connectWebcam" :class="{ active: activeSource === 'webcam' }">开启摄像头</button>
                  <button @click="disconnectWebcam" v-if="activeSource === 'webcam'" class="disconnect-button">关闭摄像头</button>
                  <button @click="uploadVideoFile" :disabled="activeSource === 'webcam'">上传视频</button>

                  <!-- 新增RTMP流连接按钮 -->
                  <button @click="showRtmpModal" :disabled="activeSource === 'webcam'" class="rtmp-button">RTMP流连接</button>

                </div>
                <!-- The hidden file input is no longer needed here -->
              </div>

              <!-- 检测模式选择 -->
              <div class="control-section">
                <h3>检测模式</h3>
                <div class="button-group">
                  <button 
                    @click="setDetectionMode('object_detection')" 
                    :class="{ active: detectionMode === 'object_detection' }">
                    目标检测
                  </button>
                  <button 
                    @click="setDetectionMode('face_only')" 
                    :class="{ active: detectionMode === 'face_only' }">
                    纯人脸识别
                  </button>
                  <button 
                    @click="setDetectionMode('fall_detection')" 
                    :class="{ active: detectionMode === 'fall_detection' }">
                    跌倒检测
                  </button>
                  <button 
                    @click="setDetectionMode('smoking_detection')" 
                    :class="{ active: detectionMode === 'smoking_detection' }">
                    抽烟检测
                  </button>
                  <button 
                    @click="setDetectionMode('violence_detection')" 
                    :class="{ active: detectionMode === 'violence_detection' }">
                    暴力检测
                  </button>
                </div>
              </div>
              
              <!-- 危险区域编辑 -->
              <div class="control-section">
                <h3>危险区域设置</h3>
                <div class="button-group">
                  <button @click="toggleEditMode" :class="{ active: editMode }">
                    {{ editMode ? '保存区域' : '编辑区域' }}
                  </button>
                  <button v-if="editMode" @click="cancelEdit">取消编辑</button>
                </div>
                <div v-if="editMode" class="edit-instructions">
                  <p>点击并拖动区域点以调整位置</p>
                  <p>右键点击删除点</p>
                  <p>双击添加新点</p>
                </div>
              </div>
              
              <!-- 参数设置 -->
              <div class="control-section">
                <h3>参数设置</h3>
                <div class="setting-row">
                  <label>安全距离 (像素)</label>
                  <input type="range" v-model="safetyDistance" min="10" max="200" step="5" />
                  <span>{{ safetyDistance }}</span>
                </div>
                <div class="setting-row">
                  <label>警报阈值 (秒)</label>
                  <input type="range" v-model="loiteringThreshold" min="0.5" max="10" step="0.5" />
                  <span>{{ loiteringThreshold }}</span>
                </div>
                <button @click="updateSettings" class="apply-button">应用设置</button>
              </div>
              
              <!-- 告警信息 -->
              <div class="control-section">
                <h3>告警信息</h3>
                <div class="alerts-container" :class="{ 'has-alerts': alerts.length > 0 }">
                  <div v-if="alerts.length > 0" class="alert-list">
                    <div v-for="(alert, index) in alerts" :key="index" class="alert-item">
                      {{ alert }}
                    </div>
                  </div>
                  <p v-else>当前无告警信息</p>
                </div>
              </div>

              <!-- 人员管理 -->
              <div class="control-section">
                <h3>人员管理</h3>
                <div class="button-group">
                  <button @click="registerFace" class="apply-button">添加人员</button>
                </div>
                <div class="user-list-container">
                  <ul v-if="registeredUsers.length > 0">
                    <li v-for="user in registeredUsers" :key="user">
                      <span>{{ user }}</span>
                      <button @click="deleteFace(user)" class="delete-button">删除</button>
                    </li>
                  </ul>
                  <p v-else>未注册任何人员</p>
                </div>
              </div>

              <!-- 新增：活动流列表 -->
              <div v-if="activeStreams.length > 0" class="control-section">
                <h3>活动RTMP流</h3>
                <div class="stream-list">
                  <div v-for="stream in activeStreams" :key="stream.stream_id" class="stream-item">
                    <div class="stream-info">
                      <h4>{{ stream.name }}</h4>
                      <p>{{ stream.rtmp_url }}</p>
                      <span class="stream-status" :class="stream.status">{{ stream.status }}</span>
                    </div>
                    <div class="stream-controls">
                      <button @click="selectRtmpStream(stream.stream_id)" class="select-button" :class="{ active: currentRtmpStream === stream.stream_id }">选择</button>
                      <button @click="stopRtmpStream(stream.stream_id)" class="stop-button">停止</button>
                      <button @click="deleteRtmpStream(stream.stream_id)" class="delete-button">删除</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { ref, onMounted, onUnmounted, nextTick } from 'vue' // 移除 watch
import io from 'socket.io-client';

// 导入侧边栏组件
import TopBar from '../components/TopBar.vue'

// 当前路径状态
const currentPath = ref('')

// API端点设置
const SERVER_ROOT_URL = '' // 使用相对路径
const API_BASE_URL = '/api'
const DLIB_API_BASE_URL = `${API_BASE_URL}/dlib`; // 新的 Dlib API 基础路径
const VIDEO_FEED_URL = `${API_BASE_URL}/video_feed`

// --- 新增：注册模态框状态 ---
const showRegistrationModal = ref(false);
const registrationStatus = ref('');
const registrationName = ref('');
const capturedFramesCount = ref(0);
const registrationVideoEl = ref(null); // video 元素的引用
const registrationSocket = ref(null); // 注册用的 WebSocket 实例
const localStream = ref(null); // 本地摄像头流
const wasWebcamActive = ref(false); // 新增：记录注册前摄像头是否开启

// --- 新增：停止媒体流的辅助函数 ---
const stopStream = (stream) => {
  if (stream && stream.getTracks) {
    stream.getTracks().forEach(track => track.stop());
  }
};

// 状态变量
const videoSource = ref('') // 视频源URL
const activeSource = ref('') // 'webcam', 'upload', 'loading', 'rtmp'
const editMode = ref(false)
const alerts = ref([])
const safetyDistance = ref(100)
const loiteringThreshold = ref(2.0)
const detectionMode = ref('object_detection') // 新增：检测模式状态
const originalDangerZone = ref([]) // V3: 初始化为空数组
const registeredUsers = ref([]) // 已注册用户列表
const pollingIntervalId = ref(null) // 用于轮询的定时器ID
const videoTaskId = ref(''); // 保存当前视频处理任务的ID
const displayImage = ref(null); // V3: 统一的图像引用

// --- V3: Canvas 和危险区域状态 ---
const interactionCanvas = ref(null);
const dangerZone = ref([]); // 用于存储和操作危险区域的点
const isDragging = ref(false);
const draggingIndex = ref(-1);

// 新增Canvas相关变量
const rtmpCanvas = ref(null)
let canvasContext = null
let currentDetections = []

// 添加Canvas尺寸状态
const canvasWidth = ref(1280)  // 默认1280
const canvasHeight = ref(720)  // 默认720
const originalWidth = ref(1280)  // 原始视频宽度
const originalHeight = ref(720)  // 原始视频高度

// 新增：RTMP流相关状态
const showRtmpConnectionModal = ref(false)
const rtmpConfig = ref({
  name: '',
  rtmp_url: '',
  description: '',
  detection_modes: ['object_detection']
})
const rtmpStatus = ref('')
const activeStreams = ref([])
const currentRtmpStream = ref('')
const rtmpSocket = ref(null)

// --- API 调用封装 ---
// 使用新的 DLIB_API_BASE_URL
const dlibApiFetch = async (endpoint, options = {}) => {
  try {
    const response = await fetch(`${DLIB_API_BASE_URL}${endpoint}`, options);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(errorData.message || `服务器错误: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`Dlib API调用失败 ${endpoint}:`, error);
    alert(`操作失败: ${error.message}`);
    throw error;
  }
};

const apiFetch = async (endpoint, options = {}) => {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(errorData.message || `服务器错误: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`API调用失败 ${endpoint}:`, error);
    alert(`操作失败: ${error.message}`);
    throw error;
  }
};

// --- 检测模式管理 ---
const loadDetectionMode = async () => {
  try {
    const data = await apiFetch('/detection_mode');
    detectionMode.value = data.mode;
    console.log('Detection mode loaded:', data.mode);
  } catch (error) {
    // apiFetch中已处理错误
  }
};

const setDetectionMode = async (mode) => {
  if (detectionMode.value === mode) return; // 如果模式未变，则不执行任何操作
  try {
    const data = await apiFetch('/detection_mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: mode })
    });
    detectionMode.value = mode; // 成功后更新前端状态
    
    // 创建一个映射来获取模式的中文名
    const modeNames = {
      'object_detection': '目标检测',
      'face_only': '纯人脸识别',
      'fall_detection': '跌倒检测',
      'smoking_detection': '抽烟检测',
      'violence_detection': '暴力检测'
    };
    alert(`检测模式已切换为: ${modeNames[mode] || mode}`);

    console.log(data.message);
  } catch (error) {
    // apiFetch中已处理错误
  }
};


// --- 配置管理 ---
const loadConfig = async () => {
  try {
    const data = await apiFetch('/config');
    safetyDistance.value = data.safety_distance;
    loiteringThreshold.value = data.loitering_threshold;
    // V3: 同时加载危险区域数据，为“进入编辑模式”做准备
    dangerZone.value = data.danger_zone || [];
    originalDangerZone.value = JSON.parse(JSON.stringify(dangerZone.value));
    console.log('Configuration loaded:', data);
  } catch (error) {
    // apiFetch中已处理错误
  }
};

const updateSettings = async () => {
  try {
    const data = await apiFetch('/update_thresholds', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        safety_distance: parseInt(safetyDistance.value),
        loitering_threshold: parseFloat(loiteringThreshold.value)
      })
    });
    alert(data.message);
  } catch (error) {
     // apiFetch中已处理错误
  }
};

// --- 人脸管理 (已更新为 Dlib API) ---
const loadRegisteredUsers = async () => {
  try {
    const data = await dlibApiFetch('/faces'); // <--- 更新API地址
    registeredUsers.value = data.names;
  } catch (error) {
    // dlibApiFetch 中已处理错误
  }
};

const deleteFace = async (name) => {
  if (confirm(`确定要删除人员 '${name}' 吗?`)) {
    try {
      const data = await dlibApiFetch(`/faces/${name}`, { method: 'DELETE' }); // <--- 更新API地址
      alert(data.message);
      loadRegisteredUsers(); // 成功后刷新列表
    } catch (error) {
      // dlibApiFetch 中已处理错误
    }
  }
};

// --- 新的交互式注册流程 ---
const registerFace = () => {
  const name = prompt("请输入要注册人员的姓名:");
  if (name && name.trim()) {
    // 检查主摄像头是否正在运行，如果是，则先停止它
    if (activeSource.value === 'webcam') {
      wasWebcamActive.value = true;
      disconnectWebcam();
    } else {
      wasWebcamActive.value = false;
    }

    registrationName.value = name.trim();
    showRegistrationModal.value = true;
    capturedFramesCount.value = 0;
    registrationStatus.value = '准备中...';
    
    // 使用 nextTick 并增加一个短暂延时，以确保摄像头已被释放
    nextTick(() => {
      setTimeout(() => {
        startRegistrationCapture();
      }, 500); // 500ms 延迟，确保后端摄像头完全释放
    });
  }
};

const startRegistrationCapture = async () => {
    if (!registrationVideoEl.value) {
        console.error("注册视频元素尚未准备好。");
        registrationStatus.value = '错误：无法访问视频元素。';
        return;
    }

    // 1. 获取本地摄像头权限
    try {
        localStream.value = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        registrationVideoEl.value.srcObject = localStream.value;
    } catch(err) {
        console.error("无法访问摄像头:", err);
        registrationStatus.value = '错误：无法访问摄像头。';
        alert('无法访问摄像头，请检查权限。');
        closeRegistrationModal();
        return;
    }

    // 2. 连接到 WebSocket
    registrationSocket.value = io(`${SERVER_ROOT_URL}/dlib/register`);

    registrationSocket.value.on('connect', () => {
        console.log('已连接到注册 WebSocket');
        registrationStatus.value = '连接成功，正在开始...';
        // 发送开始指令
        registrationSocket.value.emit('start_registration', { name: registrationName.value });
    });

    registrationSocket.value.on('status', (data) => {
        console.log('注册状态:', data.message);
        registrationStatus.value = data.message;
    });

    registrationSocket.value.on('capture_result', (data) => {
        if (data.status === 'success') {
            capturedFramesCount.value = data.count;
            registrationStatus.value = `成功捕获 ${data.count} 帧`;
        } else {
            registrationStatus.value = `捕获失败: ${data.message}`;
        }
    });

    registrationSocket.value.on('error', (data) => {
        console.error('注册 WebSocket 错误:', data.message);
        registrationStatus.value = `错误: ${data.message}`;
    });

    registrationSocket.value.on('disconnect', () => {
        console.log('已从注册 WebSocket断开');
        registrationStatus.value = '连接已断开。';
    });
};

const captureFrame = () => {
    if (!registrationVideoEl.value || !registrationSocket.value) return;

    const canvas = document.createElement('canvas');
    canvas.width = registrationVideoEl.value.videoWidth;
    canvas.height = registrationVideoEl.value.videoHeight;
    const context = canvas.getContext('2d');
    context.drawImage(registrationVideoEl.value, 0, 0, canvas.width, canvas.height);
    
    // 将帧数据转为 base64
    const imageData = canvas.toDataURL('image/jpeg');
    
    // 通过 WebSocket 发送
    registrationSocket.value.emit('frame_for_capture', { image: imageData });
    registrationStatus.value = '已发送捕获请求...';
};

// 在关闭模态框时停止视频流
const closeRegistrationModal = (isUnmounting = false) => {
  showRegistrationModal.value = false;
  registrationName.value = '';
  registrationStatus.value = '';
  capturedFramesCount.value = 0;

  // 停止摄像头
  if (localStream.value && localStream.value.getTracks) {
    localStream.value.getTracks().forEach(track => track.stop());
    localStream.value = null;
  }
  
  // 断开 socket 连接
  if (registrationSocket.value) {
    registrationSocket.value.disconnect();
    registrationSocket.value = null;
  }

  // 如果不是在组件卸载时调用，并且之前摄像头是开启的，则重新连接
  if (!isUnmounting && wasWebcamActive.value) {
    connectWebcam();
    wasWebcamActive.value = false;
  }
};


// --- 视频/图像处理 ---
const connectWebcam = () => {
  stopPolling(); // 如果有正在轮询的任务，先停止
  activeSource.value = 'webcam';
  nextTick(() => {
    if (displayImage.value) {
      displayImage.value.src = `${VIDEO_FEED_URL}?t=${new Date().getTime()}`;
    }
  });
  startAlertPolling();
};

const disconnectWebcam = async () => {
  if (activeSource.value !== 'webcam') return;

  try {
    // 向后端发送停止指令
    await fetch(`${API_BASE_URL}/stop_video_feed`, { method: 'POST' });
    console.log("已向后端发送停止摄像头指令。");
  } catch (error) {
    console.error("发送停止指令失败:", error);
  } finally {
    // 无论如何都更新前端UI
    activeSource.value = '';
    videoSource.value = '';
    stopAlertPolling(); // 停止轮询警报
  }
};

const uploadVideoFile = () => {
  // 动态创建input元素，这是一个更可靠的方法
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'video/mp4,image/jpeg,image/jpg';
  input.onchange = handleFileUpload;
  input.click();
};

const handleFileUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  stopPolling(); // 开始新的上传前，停止任何已有的轮询
  videoSource.value = '';
  activeSource.value = 'loading';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      body: formData
    });

    if (response.status === 202) {
      // 异步处理视频
      const data = await response.json();
      videoTaskId.value = data.task_id;
      startPolling(data.task_id);
    } else if (response.ok) {
      // 同步处理图片
      const data = await response.json();
      videoSource.value = `${SERVER_ROOT_URL}${data.file_url}?t=${new Date().getTime()}`;
      activeSource.value = 'upload';
      alerts.value = data.alerts || [];
      stopAlertPolling(); // 处理完成后停止轮询
    } else {
      // 处理其他HTTP错误
      const errorData = await response.json();
      throw new Error(errorData.message || '文件上传失败');
    }
  } catch (error) {
    activeSource.value = '';
    alert(error.message || '操作失败: Failed to fetch');
    console.error('File upload error:', error);
  }
};

const startPolling = (taskId) => {
  pollingIntervalId.value = setInterval(() => {
    pollTaskStatus(taskId);
  }, 2000); // 每2秒轮询一次
};

const stopPolling = () => {
  if (pollingIntervalId.value) {
    clearInterval(pollingIntervalId.value);
    pollingIntervalId.value = null;
    videoTaskId.value = '';
  }
};

const pollTaskStatus = async (taskId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/video/task_status/${taskId}`);

    if (response.status === 200) {
      // 任务完成
      stopPolling();
      const data = await response.json();
      videoSource.value = `${SERVER_ROOT_URL}${data.file_url}?t=${new Date().getTime()}`;
      activeSource.value = 'upload';
      alerts.value = data.alerts || [];
    } else if (response.status === 202) {
      // 任务仍在进行中
      console.log('Video processing...');
    } else {
      // 任务失败或出现其他错误
      stopPolling();
      const errorData = await response.json();
      throw new Error(errorData.message || '视频处理失败');
    }
  } catch (error) {
    stopPolling();
    activeSource.value = '';
    alert(error.message);
    console.error('Polling error:', error);
  }
};


// --- V3: 混合驱动的危险区域编辑 ---

// 核心绘制函数
const drawCanvas = () => {
  const canvas = interactionCanvas.value;
  if (!canvas || !editMode.value) return; // 确保只在编辑模式下绘制

  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (dangerZone.value.length < 2) return;

  // 绘制多边形区域
  ctx.beginPath();
  ctx.moveTo(dangerZone.value[0][0], dangerZone.value[0][1]);
  for (let i = 1; i < dangerZone.value.length; i++) {
    ctx.lineTo(dangerZone.value[i][0], dangerZone.value[i][1]);
  }
  ctx.closePath();
  
  // 编辑时使用更醒目的样式
  ctx.fillStyle = 'rgba(255, 0, 0, 0.3)'; // 半透明红色填充
  ctx.fill();
  ctx.strokeStyle = '#FF0000'; // 纯红色边框
  ctx.lineWidth = 2;
  ctx.stroke();

  // 绘制可拖拽的控制点
  ctx.fillStyle = '#FF0000';
  dangerZone.value.forEach(point => {
    ctx.beginPath();
    ctx.arc(point[0], point[1], 8, 0, Math.PI * 2);
    ctx.fill();
  });
};

// 当图片加载或尺寸变化时，同步Canvas尺寸
const onImageLoad = () => {
  nextTick(() => {
    const img = displayImage.value;
    const canvas = interactionCanvas.value;
    if (img && canvas && editMode.value) {
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      canvas.style.width = `${img.clientWidth}px`;
      canvas.style.height = `${img.clientHeight}px`;
      drawCanvas();
    }
  });
};


// 危险区域编辑模式切换
const toggleEditMode = async () => {
  if (!editMode.value) {
    // --- 进入编辑模式 ---
    try {
      await apiFetch('/toggle_edit_mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ edit_mode: true })
      });
      
      // 从后端加载最新的数据以开始编辑
      await loadConfig();
      
      editMode.value = true;
      // 使用nextTick确保canvas已渲染，然后再进行绘制
      nextTick(() => {
        onImageLoad(); // 该函数会处理尺寸同步和初次绘制
      });

    } catch (error) {
      console.error('进入编辑模式失败:', error);
      alert('无法进入编辑模式，请重试。');
    }
  } else {
    // --- 保存并退出编辑模式 ---
    try {
      await apiFetch('/update_danger_zone', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ danger_zone: dangerZone.value }),
      });
      
      // 通知后端退出编辑模式
      await apiFetch('/toggle_edit_mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ edit_mode: false })
      });
      
      editMode.value = false; // 这将自动隐藏Canvas
      alert('危险区域已成功保存！');

      // --- 新增：强制刷新视频流以显示更新后的区域 ---
      if (activeSource.value === 'webcam') {
        videoSource.value = `${VIDEO_FEED_URL}?t=${new Date().getTime()}`;
      } else if (activeSource.value === 'rtmp' && currentRtmpStream.value) {
        videoSource.value = `${API_BASE_URL}/streams/${currentRtmpStream.value}/feed?t=${new Date().getTime()}`;
      }

    } catch (error) {
      console.error('保存危险区域失败:', error);
      alert('保存危险区域失败，请重试。');
    }
  }
}

// 取消编辑
const cancelEdit = async () => {
  try {
    // 只需通知后端退出编辑模式即可
    await apiFetch('/toggle_edit_mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ edit_mode: false })
    });
    editMode.value = false;
  } catch (error) {
    console.error('取消编辑失败:', error);
    alert('取消编辑操作失败。');
  }
}

// 判断URL是否为图像
const isImageUrl = (url) => {
  const lowerUrl = url.toLowerCase();
  return lowerUrl.includes('.jpg') || lowerUrl.includes('.jpeg')
}

// 判断URL是否为视频
const isVideoUrl = (url) => {
  return url.toLowerCase().includes('.mp4')
}

const stopAlertPolling = () => {
  if (alertPollingInterval) {
    clearInterval(alertPollingInterval);
    alertPollingInterval = null;
  }
}

// 定期轮询告警信息
let alertPollingInterval = null

const startAlertPolling = () => {
  // 先清除之前的轮询
  if (alertPollingInterval) {
    clearInterval(alertPollingInterval)
  }
  
  // 开始新的轮询
  alertPollingInterval = setInterval(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/alerts`)
      const data = await response.json()
      alerts.value = data.alerts || []
    } catch (error) {
      console.error('Error fetching alerts:', error)
      // 如果获取告警失败（例如服务器重启），则停止轮询
      stopAlertPolling();
    }
  }, 2000) // 轮询频率调整为2秒
}

// --- RTMP流管理 ---
const showRtmpModal = () => {
  showRtmpConnectionModal.value = true
  rtmpConfig.value = {
    name: '',
    rtmp_url: '',
    description: '',
    detection_modes: ['object_detection']
  }
  rtmpStatus.value = ''
}

const closeRtmpModal = () => {
  showRtmpConnectionModal.value = false
  rtmpStatus.value = ''
}

const connectRtmpStream = async () => {
  if (!rtmpConfig.value.name || !rtmpConfig.value.rtmp_url) {
    alert('请填写流名称和RTMP地址')
    return
  }

  rtmpStatus.value = '正在连接RTMP流...'
  
  try {
    const response = await fetch(`${API_BASE_URL}/streams`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(rtmpConfig.value)
    })

    if (response.ok) {
      const data = await response.json()
      rtmpStatus.value = '流创建成功，正在启动...'
      
      // 启动流处理
      await startRtmpStream(data.stream_id)
      
      // 刷新流列表
      await loadActiveStreams()
      
      closeRtmpModal()
    } else {
      const errorData = await response.json()
      rtmpStatus.value = `连接失败: ${errorData.detail || '未知错误'}`
    }
  } catch (error) {
    rtmpStatus.value = `连接失败: ${error.message}`
    console.error('RTMP连接错误:', error)
  }
}

const startRtmpStream = async (streamId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/streams/${streamId}/start`, {
      method: 'POST'
    })
    
    if (response.ok) {
      console.log('RTMP流启动成功')
    } else {
      throw new Error('启动流失败')
    }
  } catch (error) {
    console.error('启动RTMP流错误:', error)
    alert(`启动流失败: ${error.message}`)
  }
}

const loadActiveStreams = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/streams`)
    if (response.ok) {
      const data = await response.json()
      activeStreams.value = data
    }
  } catch (error) {
    console.error('加载流列表错误:', error)
  }
}

const selectRtmpStream = (streamId) => {
  currentRtmpStream.value = streamId
  // 切换到RTMP流显示
  activeSource.value = 'rtmp'
  
  // 确保Canvas正确初始化
  nextTick(() => {
    if (rtmpCanvas.value) {
      canvasContext = rtmpCanvas.value.getContext('2d')
      console.log('Canvas上下文初始化成功')
      
      // 在Canvas初始化后再连接Socket
      setTimeout(() => {
        connectToRtmpSocket(streamId)
      }, 100)
    } else {
      console.error('Canvas元素未找到')
    }
  })
}

const connectToRtmpSocket = (streamId) => {
  // 先断开现有连接
  if (rtmpSocket.value) {
    rtmpSocket.value.disconnect()
    rtmpSocket.value = null
  }
  
  console.log(`正在连接RTMP Socket，流ID: ${streamId}`)
  
  // 修改连接配置 - 允许WebSocket优先
  rtmpSocket.value = io('/rtmp', {
    transports: ['websocket', 'polling'],  // WebSocket优先，polling作为备选
    forceNew: true,
    timeout: 20000,
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000
  })
  
  rtmpSocket.value.on('connect', () => {
    console.log(`✅ 已连接到RTMP WebSocket，流ID: ${streamId}`)
    console.log('Socket ID:', rtmpSocket.value.id)
    console.log('传输方式:', rtmpSocket.value.io.engine.transport.name)  // 添加这行来检查传输方式
    rtmpSocket.value.emit('join_stream', { stream_id: streamId })
    console.log(`📤 已发送join_stream事件，流ID: ${streamId}`)
  })
  
  rtmpSocket.value.on('connect_error', (error) => {
    console.error('❌ Socket连接错误:', error)
  })
  
  rtmpSocket.value.on('status', (data) => {
    console.log('📊 RTMP状态:', data)
  })
  
  let frameCount = 0
  rtmpSocket.value.on('video_frame', (data) => {
    frameCount++
    console.log(`📺 收到video_frame事件，帧数: ${frameCount}, 流ID: ${data.stream_id}`)
    
    if (data.stream_id === currentRtmpStream.value && canvasContext && rtmpCanvas.value) {
        // 动态更新Canvas和原始尺寸
        if (data.original_width && data.original_height) {
          // 更新原始尺寸
          originalWidth.value = data.original_width
          originalHeight.value = data.original_height
          
          // 更新Canvas尺寸为原始尺寸
          canvasWidth.value = data.original_width
          canvasHeight.value = data.original_height
          
          // 更新Canvas元素的实际尺寸
          rtmpCanvas.value.width = data.original_width
          rtmpCanvas.value.height = data.original_height
          
          console.log(`📐 Canvas尺寸已更新为: ${data.original_width}x${data.original_height}`)
        }
        
        if (data.frame_data) {
          drawVideoFrame(data.frame_data)
          console.log(`✅ 成功绘制第${frameCount}帧`)
        } else {
          console.error('❌ 收到的帧数据为空')
        }
      }
  })
  
  // 接收AI检测结果
  rtmpSocket.value.on('ai_result', (data) => {
    console.log('🔍 收到AI检测结果:', data)
    if (data.stream_id === currentRtmpStream.value) {
      currentDetections = data.detections || []
      alerts.value = data.alerts || []
      
      if (canvasContext && rtmpCanvas.value) {
        drawDetectionResults(currentDetections)
      }
    }
  })
  
  // 添加测试事件监听
  rtmpSocket.value.on('test_event', (data) => {
    console.log('🧪 收到测试事件:', data)
  })
  
  rtmpSocket.value.on('error', (error) => {
    console.error('❌ RTMP WebSocket错误:', error)
  })
  
  rtmpSocket.value.on('disconnect', (reason) => {
    console.log('🔌 RTMP WebSocket断开连接，原因:', reason)
  })
}

const stopRtmpStream = async (streamId) => {
  try {
    console.log(`正在停止流: ${streamId}`);
    const response = await fetch(`${API_BASE_URL}/streams/${streamId}/stop`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })
    
    console.log('停止流响应状态:', response.status);
    
    if (response.ok) {
      const result = await response.json();
      console.log('停止流成功:', result);
      
      if (currentRtmpStream.value === streamId) {
        activeSource.value = ''
        videoSource.value = ''
        currentRtmpStream.value = ''
        if (rtmpSocket.value) {
          rtmpSocket.value.disconnect()
          rtmpSocket.value = null
        }
      }
      await loadActiveStreams()
      alert('流停止成功!');
    } else {
      const errorData = await response.json();
      throw new Error(errorData.error || `HTTP ${response.status}`);
    }
  } catch (error) {
    console.error('停止RTMP流错误:', error)
    alert(`停止流失败: ${error.message}`)
  }
}

const deleteRtmpStream = async (streamId) => {
  if (confirm('确定要删除这个RTMP流吗？')) {
    try {
      console.log(`正在删除流: ${streamId}`);
      const response = await fetch(`${API_BASE_URL}/streams/${streamId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      console.log('删除流响应状态:', response.status);
      
      if (response.ok) {
        const result = await response.json();
        console.log('删除流成功:', result);
        
        if (currentRtmpStream.value === streamId) {
          activeSource.value = ''
          videoSource.value = ''
          currentRtmpStream.value = ''
          if (rtmpSocket.value) {
            rtmpSocket.value.disconnect()
            rtmpSocket.value = null
          }
        }
        await loadActiveStreams()
        alert('流删除成功!');
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }
    } catch (error) {
      console.error('删除RTMP流错误:', error)
      alert(`删除流失败: ${error.message}`)
    }
  }
}


// 绘制视频帧到Canvas
const drawVideoFrame = (frameData) => {
  try {
    if (!canvasContext || !rtmpCanvas.value) {
      console.warn('⚠️ Canvas未准备好，跳过帧绘制')
      return
    }
    
    if (!frameData) {
      console.error('❌ 帧数据为空')
      return
    }
    
    // 确保frameData是ArrayBuffer或Uint8Array
    let binaryData
    if (frameData instanceof ArrayBuffer) {
      binaryData = frameData
    } else if (frameData instanceof Uint8Array) {
      binaryData = frameData.buffer
    } else if (typeof frameData === 'object' && frameData.data) {
      // 处理可能的Buffer对象
      binaryData = new Uint8Array(frameData.data).buffer
    } else {
      console.error('❌ 不支持的帧数据格式:', typeof frameData)
      return
    }
    
    // 将二进制数据转换为Blob
    const blob = new Blob([binaryData], { type: 'image/jpeg' })
    
    // 创建临时URL
    const imageUrl = URL.createObjectURL(blob)
    
    // 创建Image对象
    const img = new Image()
    img.onload = () => {
      try {
        // 清除Canvas
        canvasContext.clearRect(0, 0, rtmpCanvas.value.width, rtmpCanvas.value.height)
        
        // 绘制图像到Canvas
        canvasContext.drawImage(img, 0, 0, rtmpCanvas.value.width, rtmpCanvas.value.height)
        
        // 绘制检测结果
        drawDetectionResults(currentDetections)
        
        // 释放临时URL
        URL.revokeObjectURL(imageUrl)
      } catch (drawError) {
        console.error('❌ 绘制图像到Canvas失败:', drawError)
      }
    }
    
    img.onerror = () => {
      console.error('❌ 图像加载失败')
      URL.revokeObjectURL(imageUrl)
    }
    
    img.src = imageUrl
    
  } catch (error) {
    console.error('❌ 绘制视频帧错误:', error)
  }
}

// 在Canvas上绘制AI检测结果
const drawDetectionResults = (detections) => {
  if (!canvasContext || !detections || detections.length === 0) return
  
  detections.forEach(detection => {
    const { type, bbox, confidence, message, keypoints } = detection
    const [x1, y1, x2, y2] = bbox
    
    // 设置样式
    canvasContext.strokeStyle = type === 'fall' ? '#ff0000' : 
                               type === 'pose' ? '#00ff00' : 
                               type === 'object' ? '#00ff00' : '#0099ff'
    canvasContext.lineWidth = 2
    canvasContext.fillStyle = type === 'fall' ? '#ff0000' : 
                             type === 'pose' ? '#00ff00' : 
                             type === 'object' ? '#00ff00' : '#0099ff'
    canvasContext.font = '14px Arial'
    
    // 绘制边界框
    canvasContext.strokeRect(x1, y1, x2 - x1, y2 - y1)
    
    // 绘制标签
    const label = `${message || type} (${(confidence * 100).toFixed(1)}%)`
    const textWidth = canvasContext.measureText(label).width
    
    // 绘制标签背景
    canvasContext.fillRect(x1, y1 - 25, textWidth + 10, 20)
    
    // 绘制标签文字
    canvasContext.fillStyle = '#ffffff'
    canvasContext.fillText(label, x1 + 5, y1 - 10)
    
    // 如果是姿态检测，绘制关键点和骨架
    if ((type === 'fall' || type === 'pose') && keypoints) {
      drawPoseKeypoints(keypoints)
    }
  })
}

// 新增：绘制人体关键点和骨架的函数
const drawPoseKeypoints = (keypoints) => {
  if (!canvasContext || !keypoints) return
  
  // YOLO姿态关键点连接定义（17个关键点）
  const connections = [
    [0, 1], [0, 2], [1, 3], [2, 4],  // 头部
    [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],  // 手臂
    [5, 11], [6, 12], [11, 12],  // 躯干
    [11, 13], [13, 15], [12, 14], [14, 16]  // 腿部
  ]
  
  // 绘制骨架连接
  canvasContext.strokeStyle = '#ff6b6b'
  canvasContext.lineWidth = 2
  
  connections.forEach(([start, end]) => {
    if (start < keypoints.length && end < keypoints.length) {
      const startPoint = keypoints[start]
      const endPoint = keypoints[end]
      
      // 检查关键点是否可见（置信度 > 0.5）
      if (startPoint[2] > 0.5 && endPoint[2] > 0.5) {
        canvasContext.beginPath()
        canvasContext.moveTo(startPoint[0], startPoint[1])
        canvasContext.lineTo(endPoint[0], endPoint[1])
        canvasContext.stroke()
      }
    }
  })
  
  // 绘制关键点
  canvasContext.fillStyle = '#4ecdc4'
  keypoints.forEach((point, index) => {
    if (point[2] > 0.5) {  // 置信度阈值
      canvasContext.beginPath()
      canvasContext.arc(point[0], point[1], 4, 0, 2 * Math.PI)
      canvasContext.fill()
    }
  })
}


// 生命周期钩子
onMounted(() => {
  loadConfig()
  loadRegisteredUsers() // 页面加载时获取已注册用户
  loadDetectionMode() // 新增：页面加载时获取当前检测模式
  loadActiveStreams() // 新增：加载活动流列表
})

onUnmounted(() => {
  // 清除定时器
  if (pollingIntervalId.value) {
    clearInterval(pollingIntervalId.value)
  }
  
  // 停止所有正在运行的视频流
  disconnectWebcam(); // 这个函数现在会处理摄像头关闭
  closeRegistrationModal(true); // 组件卸载时确保清理, 并告知函数不要重启摄像头
  
  // 新增：清理RTMP WebSocket连接
  if (rtmpSocket.value) {
    rtmpSocket.value.disconnect()
  }
});
</script>

<style scoped>
/* 复用的布局样式 */
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #121212;
  color: #e0e0e0;
}

/* 顶部导航栏样式 */
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  height: 60px;
  background-color: #1e1e1e;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #e0e0e0;
}

.header-right {
  display: flex;
  align-items: center;
}

.profile-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  overflow: hidden;
  border: 2px solid rgba(255, 255, 255, 0.3);
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.name-role h2 {
  margin: 0;
  font-size: 16px;
  color: #e0e0e0;
}

.name-role p {
  margin: 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

/* 主内容区域样式 */
.main-content {
  display: flex;
  flex: 1;
  height: calc(100vh - 60px);
}

/* 内容区域样式 */
.content-area {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background-color: #121212;
}

/* 实时视频监控页面特有样式 */
.monitor-page {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
  color: #fff;
  background-color: #1a1a1a;
  border-radius: 8px;
}

.monitor-page h1 {
  text-align: center;
  margin-bottom: 2rem;
  color: #e0e0e0;
}
.monitor-container {
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
}
.video-container, .control-panel {
  flex: 1;
  min-width: 300px;
  border-radius: 8px;
  padding: 1.5rem;
  background-color: #2d2d2d;
}
.video-container h2, .control-panel h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid #444;
  padding-bottom: 0.5rem;
  color: #e0e0e0;
}
.video-wrapper {
  width: 100%;
  height: 480px;
  background-color: #000;
  border: 1px solid #444;
  border-radius: 4px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative; /* 必须是相对定位，作为Canvas绝对定位的基准 */
}

/* V3: 交互式Canvas的样式 */
.interaction-canvas {
  position: absolute;
  top: 0;
  left: 0;
  /* width 和 height 将由JS根据图像大小设置 */
  cursor: crosshair;
}

.webcam-feed {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.video-wrapper img, .video-wrapper video {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.video-placeholder, .loading-state {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #888;
}

.loading-spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin-top: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.control-section {
  margin-bottom: 2rem;
}
.control-section h3 {
  margin-bottom: 1rem;
  color: #ccc;
}
/* 控制面板按钮组样式 */
.control-panel .button-group {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}
.control-panel .button-group button, .apply-button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  background-color: #4CAF50;
  color: white;
  cursor: pointer;
  transition: background-color 0.3s;
}
.control-panel .button-group button:hover, .apply-button:hover {
  background-color: #45a049;
}
.control-panel .button-group button.active {
  background-color: #007BFF;
}

.control-panel .button-group button:disabled {
  background-color: #555;
  cursor: not-allowed;
}

/* 关闭摄像头按钮样式 */
.disconnect-button {
  background-color: #f44336 !important;
}
.disconnect-button:hover {
  background-color: #d32f2f !important;
}

.edit-instructions {
  font-size: 0.9rem;
  color: #aaa;
  margin-top: 1rem;
  background-color: #2a2a2e;
  padding: 0.8rem;
  border-radius: 4px;
  border-left: 3px solid #007BFF;
}

.setting-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
  padding: 0.5rem 0;
}

.setting-row label {
  flex-basis: 120px;
  color: #ddd;
}

.setting-row input[type="range"] {
  flex-grow: 1;
  accent-color: #4CAF50;
}

.setting-row span {
  min-width: 40px;
  text-align: center;
  color: #ddd;
  background-color: #3a3a3a;
  padding: 0.2rem 0.5rem;
  border-radius: 3px;
}

.alerts-container {
  height: 150px;
  overflow-y: auto;
  border: 1px solid #444;
  padding: 0.5rem;
  border-radius: 4px;
  background-color: #2a2a2e;
}

.alerts-container.has-alerts {
  border-color: #f44336;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.alert-item {
  background-color: #533;
  padding: 0.5rem;
  border-radius: 4px;
  color: #ffcccc;
  border-left: 3px solid #f44336;
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateX(-10px); }
  to { opacity: 1; transform: translateX(0); }
}

.user-list-container {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #444;
  padding: 0.5rem;
  border-radius: 4px;
  background-color: #2a2a2e;
}

.user-list-container ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.user-list-container li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  border-bottom: 1px solid #333;
  transition: background-color 0.2s;
}

.user-list-container li:hover {
  background-color: #3a3a3a;
}

.user-list-container li:last-child {
  border-bottom: none;
}

.delete-button {
  padding: 0.2rem 0.5rem;
  background-color: #f44336;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.delete-button:hover {
  background-color: #d32f2d;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .header-left h1 {
    font-size: 16px;
  }
  
  .monitor-container {
    flex-direction: column;
  }
  
  .video-wrapper {
    height: 320px;
  }
  
  .setting-row {
    flex-wrap: wrap;
  }
  
  .setting-row label {
    flex-basis: 100%;
    margin-bottom: 0.5rem;
  }
}

/* 新增：注册模态框样式 */
.registration-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.registration-modal-content {
  background-color: #2c2c2c;
  padding: 30px;
  border-radius: 10px;
  border: 1px solid #444;
  color: #fff;
  width: 800px;
  max-width: 90%;
  text-align: center;
}

.registration-modal-content h2 {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 1.8em;
  color: #4CAF50; /* 主题绿色 */
}

.registration-video-container {
  width: 100%;
  margin-bottom: 20px;
  background-color: #000;
  border-radius: 5px;
  overflow: hidden;
}

.registration-video {
  width: 100%;
  height: auto;
  display: block;
}

.registration-status {
  margin-bottom: 20px;
  font-size: 1.1em;
  background-color: #333;
  padding: 10px;
  border-radius: 5px;
}

.registration-controls {
  display: flex;
  justify-content: center;
  gap: 20px;
}

.registration-controls button {
  padding: 12px 25px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 1.1em;
  transition: background-color 0.3s ease;
}

.capture-button {
  background-color: #007bff;
  color: white;
}
.capture-button:hover {
  background-color: #0056b3;
}

.finish-button {
  background-color: #4CAF50;
  color: white;
}
.finish-button:hover {
  background-color: #45a049;
}

/* 新增：RTMP模态框样式 */
.rtmp-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.rtmp-modal-content {
  background-color: #2c2c2c;
  padding: 30px;
  border-radius: 10px;
  border: 1px solid #444;
  color: #fff;
  width: 600px;
  max-width: 90%;
}

.rtmp-modal-content h2 {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 1.8em;
  color: #FF9800;
  text-align: center;
}

.rtmp-form {
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  color: #ddd;
  font-weight: bold;
}

.rtmp-input {
  width: 100%;
  padding: 10px;
  border: 1px solid #555;
  border-radius: 5px;
  background-color: #333;
  color: #fff;
  font-size: 14px;
}

.rtmp-input:focus {
  outline: none;
  border-color: #FF9800;
}

.detection-modes {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #ddd;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  accent-color: #FF9800;
}

.rtmp-controls {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-bottom: 15px;
}

.connect-button {
  background-color: #4CAF50;
  color: white;
  padding: 12px 25px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 1.1em;
  transition: background-color 0.3s ease;
}

.connect-button:hover:not(:disabled) {
  background-color: #45a049;
}

.connect-button:disabled {
  background-color: #555;
  cursor: not-allowed;
}

.cancel-button {
  background-color: #f44336;
  color: white;
  padding: 12px 25px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 1.1em;
  transition: background-color 0.3s ease;
}

.cancel-button:hover {
  background-color: #d32f2f;
}

.rtmp-status {
  text-align: center;
  padding: 10px;
  background-color: #333;
  border-radius: 5px;
  color: #ddd;
}

/* RTMP流连接按钮样式 */
.rtmp-button {
  background-color: #FF9800 !important;
}
.rtmp-button:hover {
  background-color: #F57C00 !important;
}

/* 活动流列表样式 */
.stream-list {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #444;
  border-radius: 5px;
  background-color: #2a2a2e;
}

.stream-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border-bottom: 1px solid #333;
  transition: background-color 0.2s;
}

.stream-item:hover {
  background-color: #3a3a3a;
}

.stream-item:last-child {
  border-bottom: none;
}

.stream-info h4 {
  margin: 0 0 5px 0;
  color: #e0e0e0;
}

.stream-info p {
  margin: 0 0 5px 0;
  color: #aaa;
  font-size: 0.9em;
  word-break: break-all;
}

.stream-status {
  padding: 3px 8px;
  border-radius: 3px;
  font-size: 0.8em;
  font-weight: bold;
}

.stream-status.active {
  background-color: #4CAF50;
  color: white;
}

.stream-status.inactive {
  background-color: #757575;
  color: white;
}

.stream-status.error {
  background-color: #f44336;
  color: white;
}

.stream-controls {
  display: flex;
  gap: 8px;
}

.select-button, .stop-button {
  padding: 6px 12px;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.9em;
  transition: background-color 0.2s;
}

.select-button {
  background-color: #2196F3;
  color: white;
}

.select-button:hover {
  background-color: #1976D2;
}

.select-button.active {
  background-color: #FF9800;
}

.stop-button {
  background-color: #FF5722;
  color: white;
}

.stop-button:hover {
  background-color: #E64A19;
}

.stream-controls .delete-button {
  background-color: #dc3545;
  color: white;
}

.stream-controls .delete-button:hover {
  background-color: #c82333;
}

/* 新增Canvas样式 */
.rtmp-canvas {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background-color: #000;
  border: 1px solid #444;
}
</style>