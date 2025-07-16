<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
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

    <div class="main-content">
      <!-- 引入复用的侧边栏组件 -->
      <Sidebar :currentPath="currentPath" />

      <!-- 主内容区域 - 入站人脸监控内容 -->
      <main class="content-area">
        <div class="monitor-page">
          <h1>入站人脸监控</h1>
          
          <div class="monitor-container">
            <div class="video-container">
              <h2>监控视图</h2>
              <div class="video-wrapper">
                <!-- Case 1: Webcam is active -->
                <img v-if="activeSource === 'webcam'" :src="videoSource" alt="摄像头实时画面" class="webcam-feed" />
                
                <!-- Case 2: An upload is active, so we check its type -->
                <template v-else-if="activeSource === 'upload'">
                    <img v-if="isImageUrl(videoSource)" :src="videoSource" alt="上传的图像" />
                    <video v-else-if="isVideoUrl(videoSource)" :src="videoSource" controls autoplay></video>
                </template>

                <!-- Case 3: Loading -->
                <div v-else-if="activeSource === 'loading'" class="loading-state">
                  <p>正在处理文件，请稍候...</p>
                  <div class="loading-spinner"></div>
                </div>
                
                <!-- Case 4: Default placeholder -->
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
                </div>
                <input 
                  type="file" 
                  ref="fileInput"
                  accept="video/mp4,image/jpeg,image/jpg"
                  style="display:none"
                  @change="handleFileUpload"
                />
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
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { ref, onMounted, onUnmounted } from 'vue'
// 导入侧边栏组件
import Sidebar from '../components/Sidebar.vue'

// 获取当前路由路径
const route = useRoute()
const currentPath = route.path

// API端点设置
const SERVER_ROOT_URL = 'http://localhost:5000'
const API_BASE_URL = `${SERVER_ROOT_URL}/api`
const VIDEO_FEED_URL = `${API_BASE_URL}/video_feed`

// 状态变量
const videoSource = ref('') // 视频源URL
const activeSource = ref('') // 'webcam', 'upload', 'loading'
const detectionMode = ref('face_only'); // 始终为face_only模式
const alerts = ref([])
const fileInput = ref(null) // 文件输入引用
const registeredUsers = ref([]) // 已注册用户列表
const pollingIntervalId = ref(null) // 用于轮询的定时器ID
const videoTaskId = ref('') // 保存当前视频处理任务的ID


// --- API 调用封装 ---
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
    throw error; // 重新抛出错误以便调用者可以捕获
  }
};

// --- 人脸管理 ---
const loadRegisteredUsers = async () => {
  try {
    const data = await apiFetch('/faces/');
    registeredUsers.value = data.names;
  } catch (error) {
    // apiFetch中已处理错误
  }
};

const registerFace = () => {
  const name = prompt("请输入要注册人员的姓名:");
  if (name) {
    // 触发隐藏的文件输入框
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/jpeg,image/jpg,image/png';
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (file) {
        handleFaceUpload(file, name);
      }
    };
    input.click();
  }
};

const handleFaceUpload = async (file, name) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('name', name);

  try {
    const data = await apiFetch('/faces/register', {
      method: 'POST',
      body: formData,
    });
    alert(data.message);
    loadRegisteredUsers(); // 成功后刷新列表
  } catch (error) {
    // apiFetch中已处理错误
  }
};

const deleteFace = async (name) => {
  if (confirm(`确定要删除人员 '${name}' 吗?`)) {
    try {
      const data = await apiFetch(`/faces/${name}`, { method: 'DELETE' });
      alert(data.message);
      loadRegisteredUsers(); // 成功后刷新列表
    } catch (error) {
      // apiFetch中已处理错误
    }
  }
};

// --- 视频/图像处理 ---
const connectWebcam = () => {
  stopPolling(); // 如果有正在轮询的任务，先停止
  // 添加时间戳来防止浏览器缓存
  videoSource.value = `${VIDEO_FEED_URL}?t=${new Date().getTime()}`;
  activeSource.value = 'webcam';
  startAlertPolling();
};

const disconnectWebcam = async () => {
  try {
    await apiFetch('/stop_video_feed', { method: 'POST' });
    videoSource.value = '';
    activeSource.value = '';
    stopAlertPolling(); // 停止轮询告警信息
    console.log('Webcam disconnected.');
  } catch (error) {
    console.error('Failed to disconnect webcam:', error);
    alert('关闭摄像头失败。');
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

// 判断URL是否为图像
const isImageUrl = (url) => {
  const lowerUrl = url.toLowerCase();
  return lowerUrl.includes('.jpg') || lowerUrl.includes('.jpeg')
}

// 判断URL是否为视频
const isVideoUrl = (url) => {
  return url.toLowerCase().includes('.mp4')
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
  }, 2000) // 轮询频率为2秒
}

const stopAlertPolling = () => {
  if (alertPollingInterval) {
    clearInterval(alertPollingInterval);
    alertPollingInterval = null;
  }
}
// 新增：强制设置后端检测模式为face_only（参考示例页面的setDetectionMode）
const forceFaceOnlyMode = async () => {
  try {
    // 调用与示例页面相同的模式切换API
    await apiFetch('/detection_mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'face_only' })
    });
    console.log('已强制设置为纯人脸识别模式');
  } catch (error) {
    console.error('设置人脸识别模式失败:', error);
  }
};

// 修改生命周期钩子，添加模式强制设置
onMounted(() => {
  loadRegisteredUsers();
  forceFaceOnlyMode(); // 页面加载时执行，确保后端模式正确
});

onUnmounted(() => {
  if (alertPollingInterval) {
    clearInterval(alertPollingInterval)
  }
  stopPolling(); // 组件卸载时确保停止轮询
})
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

/* 入站人脸页面特有样式 */
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
  position: relative;
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
}

.delete-button:hover {
  background-color: #d32f2d;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .header-left h1 {
    font-size: 16px;
  }
}
</style>
    