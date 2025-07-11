<template>
  <div class="monitor-page">
    <h1>实时视频监控系统</h1>
    
    <div class="monitor-container">
      <div class="video-container">
        <h2>监控视图</h2>
        <div class="video-wrapper">
          <!-- Case 1: Webcam is active -->
          <img v-if="activeSource === 'webcam'" :src="videoSource" alt="摄像头实时画面" />
          
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
          
          <!-- Case 4: RTMP streams are active -->
          <div v-else-if="activeSource === 'rtmp'" class="rtmp-grid">
            <div v-if="rtmpConnected && rtmpStreams.length > 0" class="streams-grid" :class="getGridClass()">
              <div v-for="(stream, index) in rtmpStreams" :key="index" class="stream-item">
                <div class="stream-header">
                  <h4>流 {{ index + 1 }}</h4>
                  <span class="stream-status" :class="{ connected: stream.connected, error: stream.error }">{{ getStreamStatus(stream) }}</span>
                </div>
                <img v-if="stream.connected" :src="getStreamUrl(index)" :alt="`RTMP流 ${index + 1}`" class="stream-video" />
                <div v-else-if="stream.error" class="stream-error">
                  <p>连接失败</p>
                  <small>{{ stream.errorMessage }}</small>
                </div>
                <div v-else class="stream-loading">
                  <p>连接中...</p>
                  <div class="loading-spinner"></div>
                </div>
              </div>
            </div>
            <div v-else class="no-streams">
              <p>请配置并连接RTMP流</p>
            </div>
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
            <button @click="toggleRtmpMode" :class="{ active: activeSource === 'rtmp' }">多RTMP流</button>
          </div>
          <input 
            type="file" 
            ref="fileInput"
            accept="video/mp4,image/jpeg,image/jpg"
            style="display:none"
            @change="handleFileUpload"
          />
          
          <!-- RTMP流配置区域 -->
          <div v-if="activeSource === 'rtmp'" class="rtmp-config">
            <h4>RTMP流配置</h4>
            <div v-for="(stream, index) in rtmpStreams" :key="index" class="rtmp-stream-item">
              <div class="rtmp-input-group">
                <label>推流地址 {{ index + 1 }}:</label>
                <input 
                  type="text" 
                  v-model="stream.url" 
                  placeholder="rtmp://example.com/live/stream"
                  class="rtmp-input"
                />
                <button @click="removeRtmpStream(index)" class="remove-button" v-if="rtmpStreams.length > 1">删除</button>
              </div>
            </div>
            <div class="rtmp-controls">
              <button @click="addRtmpStream" class="add-button">添加RTMP流</button>
              <button @click="connectRtmpStreams" class="connect-button" :disabled="!hasValidRtmpUrls">连接所有流</button>
              <button @click="disconnectRtmpStreams" v-if="rtmpConnected" class="disconnect-button">断开连接</button>
            </div>
          </div>
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
        <div class="alert-section">
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
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

// API端点设置
// 使用相对路径替代硬编码的服务器地址
const API_BASE_URL = '/api'
const VIDEO_FEED_URL = `${API_BASE_URL}/video_feed`

// 状态变量
const videoSource = ref('')
const activeSource = ref('')
const editMode = ref(false)
const alerts = ref([])
const safetyDistance = ref(100)
const loiteringThreshold = ref(2.0)
const originalDangerZone = ref(null)
const fileInput = ref(null)
const faceFileInput = ref(null) // 用于人脸注册的文件输入
const registeredUsers = ref([]) // 已注册用户列表

// RTMP流相关状态变量
const rtmpStreams = ref([{ url: '', connected: false, error: false, errorMessage: '' }])
const rtmpConnected = ref(false)
const hasValidRtmpUrls = computed(() => {
  return rtmpStreams.value.some(stream => stream.url.trim() !== '')
})

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
    alert(`检测模式已切换为: ${mode === 'object_detection' ? '目标检测' : '纯人脸识别'}`);
    console.log(data.message);
  } catch (error) {
    // apiFetch中已处理错误
  }
};


// --- 配置管理 ---
const loadConfig = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/config`)
    const data = await response.json()
    safetyDistance.value = data.safety_distance
    loiteringThreshold.value = data.loitering_threshold
    console.log('Configuration loaded:', data)
  } catch (error) {
    console.error('Error loading configuration:', error)
  }
}

// 更新设置
const updateSettings = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/update_thresholds`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        safety_distance: parseInt(safetyDistance.value),
        loitering_threshold: parseFloat(loiteringThreshold.value)
      })
    })
    const data = await response.json()
    alert(data.message)
  } catch (error) {
    console.error('Error updating settings:', error)
    alert('更新设置失败')
  }
}

// 连接摄像头流
const connectWebcam = () => {
  // 关键修复：添加时间戳来防止浏览器缓存
  videoSource.value = `${VIDEO_FEED_URL}?t=${new Date().getTime()}`
  activeSource.value = 'webcam'
  startAlertPolling()
}

// 上传视频文件
const uploadVideoFile = () => {
  fileInput.value.click()
}

// 处理文件上传
const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  // 显示加载状态
  videoSource.value = ''
  activeSource.value = 'loading'
  
  // 检查文件类型
  const fileType = file.type
  if (!fileType.includes('video/mp4') && !fileType.includes('image/jpeg') && !fileType.includes('image/jpg')) {
    alert('只支持MP4视频或JPG图片文件')
    activeSource.value = ''
    return
  }
  
  const formData = new FormData()
  formData.append('file', file)
  
  try {
    console.log('开始上传文件:', file.name, '类型:', file.type)
    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      body: formData
    });
    
    // 使用时间戳确保视频/图像被重新加载
    // 使用相对路径替代硬编码的服务器地址
    videoSource.value = `${data.file_url}?t=${new Date().getTime()}`;
    activeSource.value = 'upload';
    
    // 加载返回的告警信息
    alerts.value = data.alerts || [];
    stopAlertPolling(); // 处理完成后停止轮询

  } catch (error) {
    console.error('上传文件错误:', error)
    alert(`上传文件出错: ${error.message}`)
    activeSource.value = ''
  }
};

// --- RTMP流管理 ---
const toggleRtmpMode = () => {
  if (activeSource.value === 'rtmp') {
    // 如果已经是RTMP模式，则断开连接
    disconnectRtmpStreams();
  } else {
    // 切换到RTMP模式
    activeSource.value = 'rtmp';
    rtmpConnected.value = false;
    stopAlertPolling();
  }
};

const addRtmpStream = () => {
  rtmpStreams.value.push({ url: '', connected: false, error: false, errorMessage: '' });
};

const removeRtmpStream = (index) => {
  if (rtmpStreams.value.length > 1) {
    rtmpStreams.value.splice(index, 1);
  }
};

const connectRtmpStreams = async () => {
  const validStreams = rtmpStreams.value.filter(stream => stream.url.trim() !== '');
  if (validStreams.length === 0) {
    console.log('请至少输入一个有效的RTMP流地址');
    return;
  }

  try {
    // 清除URL缓存，确保使用新的连接
    clearStreamUrlCache();

    // 重置所有流的状态
    rtmpStreams.value.forEach(stream => {
      if (stream.url.trim() !== '') {
        stream.connected = false;
        stream.error = false;
        stream.errorMessage = '';
      }
    });

    // 直接标记为连接状态，不再调用后端连接API
    rtmpConnected.value = true;
    
    // 为每个有效流设置连接状态
    validStreams.forEach((stream, index) => {
      const streamIndex = rtmpStreams.value.findIndex(s => s.url.trim() === stream.url.trim());
      if (streamIndex !== -1) {
        rtmpStreams.value[streamIndex].connected = true;
        rtmpStreams.value[streamIndex].error = false;
        rtmpStreams.value[streamIndex].errorMessage = '';
      }
    });
    
    startAlertPolling();
    console.log(`准备显示 ${validStreams.length} 个RTMP流`);
    
  } catch (error) {
    console.error('连接RTMP流时出错:', error);
    rtmpStreams.value.forEach(stream => {
      if (stream.url.trim() !== '') {
        stream.error = true;
        stream.errorMessage = error.message;
      }
    });
  }
};

const disconnectRtmpStreams = async () => {
  try {
    await apiFetch('/rtmp/disconnect', { method: 'POST' });
    rtmpConnected.value = false;
    rtmpStreams.value.forEach(stream => {
      stream.connected = false;
      stream.error = false;
      stream.errorMessage = '';
    });
    activeSource.value = '';
    stopAlertPolling();
    // 清除URL缓存
    clearStreamUrlCache();
    console.log('RTMP streams disconnected.');
  } catch (error) {
    console.error('Failed to disconnect RTMP streams:', error);
  }
};

// 为每个流缓存URL，避免重复生成时间戳
const streamUrls = ref(new Map());

const getStreamUrl = (index) => {
  const stream = rtmpStreams.value[index];
  if (!stream || !stream.url.trim()) {
    return '';
  }
  
  // 检查是否已经为这个流生成了URL
  const streamKey = `${index}-${stream.url.trim()}`;
  if (streamUrls.value.has(streamKey)) {
    return streamUrls.value.get(streamKey);
  }
  
  // 使用Base64编码RTMP URL，只在首次连接时添加时间戳
  const encodedUrl = btoa(stream.url.trim());
  const url = `${API_BASE_URL}/rtmp/video/${encodedUrl}`;
  
  // 缓存URL
  streamUrls.value.set(streamKey, url);
  return url;
};

// 清除URL缓存的辅助方法
const clearStreamUrlCache = () => {
  streamUrls.value.clear();
};

const getStreamStatus = (stream) => {
  if (stream.connected) return '已连接';
  if (stream.error) return '连接失败';
  return '连接中...';
};

const getGridClass = () => {
  const count = rtmpStreams.value.filter(s => s.url.trim() !== '').length;
  if (count === 1) return 'grid-1';
  if (count === 2) return 'grid-2';
  if (count <= 4) return 'grid-4';
  if (count <= 6) return 'grid-6';
  return 'grid-9';
};


// 危险区域编辑模式
const toggleEditMode = async () => {
  if (!editMode.value) {
    // 进入编辑模式
    try {
      // 保存原始危险区域以便取消时恢复
      const response = await fetch(`${API_BASE_URL}/config`)
      const data = await response.json()
      originalDangerZone.value = data.danger_zone
      
      // 切换到编辑模式
      await fetch(`${API_BASE_URL}/toggle_edit_mode`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ edit_mode: true })
      })
      
      editMode.value = true
    } catch (error) {
      console.error('Error entering edit mode:', error)
      alert('无法进入编辑模式')
    }
  } else {
    // 退出编辑模式，保存更改
    try {
      // 获取更新后的危险区域
      const response = await fetch(`${API_BASE_URL}/config`)
      const data = await response.json()
      
      // 保存新的危险区域
      await fetch(`${API_BASE_URL}/update_danger_zone`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ danger_zone: data.danger_zone })
      })
      
      // 退出编辑模式
      await fetch(`${API_BASE_URL}/toggle_edit_mode`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ edit_mode: false })
      })
      
      editMode.value = false
      alert('危险区域已保存')
    } catch (error) {
      console.error('Error saving danger zone:', error)
      alert('保存危险区域失败')
    }
  }
}

// 取消编辑，恢复原始危险区域
const cancelEdit = async () => {
  if (!originalDangerZone.value) return
  
  try {
    // 恢复原始危险区域
    await fetch(`${API_BASE_URL}/update_danger_zone`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ danger_zone: originalDangerZone.value })
    })
    
    // 退出编辑模式
    await fetch(`${API_BASE_URL}/toggle_edit_mode`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ edit_mode: false })
    })
    
    editMode.value = false
  } catch (error) {
    console.error('Error canceling edit:', error)
    alert('取消编辑失败')
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
    }
  }, 3000)
}

// 生命周期钩子
onMounted(() => {
  loadConfig()
})

onUnmounted(() => {
  if (alertPollingInterval) {
    clearInterval(alertPollingInterval)
  }
})
</script>

<style>
.monitor-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

h1 {
  text-align: center;
  margin-bottom: 30px;
  color: #2c3e50;
}

.monitor-container {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.video-container {
  flex: 2;
  min-width: 640px;
}

.control-panel {
  flex: 1;
  min-width: 300px;
}

.video-wrapper {
  width: 100%;
  height: 480px;
  background-color: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 5px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-wrapper img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.video-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #555;
}

.loading-spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin-top: 10px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.control-section {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f9f9f9;
  border-radius: 5px;
  border: 1px solid #eee;
}

h2 {
  margin-bottom: 15px;
  color: #2c3e50;
}

h3 {
  margin-bottom: 10px;
  color: #2c3e50;
  font-size: 16px;
}

.button-group {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

button {
  padding: 8px 12px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

button:hover {
  background-color: #45a049;
}

button.active {
  background-color: #2196F3;
}

.setting-row {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
  gap: 10px;
}

.setting-row label {
  flex: 1;
}

.setting-row input {
  flex: 2;
}

.setting-row span {
  flex: 0 0 40px;
  text-align: right;
}

.apply-button {
  width: 100%;
  margin-top: 10px;
}

.alert-section {
  margin-top: 30px;
}

.alerts-container {
  max-height: 200px;
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
  background-color: #d32f2f;
}

/* RTMP流相关样式 */
.rtmp-config {
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid #444;
  border-radius: 4px;
  background-color: #2a2a2e;
}

.rtmp-config h4 {
  margin: 0 0 1rem 0;
  color: #ccc;
}

.rtmp-stream-item {
  margin-bottom: 1rem;
}

.rtmp-input-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.rtmp-input-group label {
  min-width: 100px;
  color: #ccc;
}

.rtmp-input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #555;
  border-radius: 4px;
  background-color: #333;
  color: #fff;
}

.rtmp-input:focus {
  outline: none;
  border-color: #007BFF;
}

.rtmp-controls {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.add-button {
  background-color: #28a745 !important;
}

.add-button:hover {
  background-color: #218838 !important;
}

.connect-button {
  background-color: #007BFF !important;
}

.connect-button:hover {
  background-color: #0056b3 !important;
}

.remove-button {
  background-color: #dc3545 !important;
  padding: 0.3rem 0.6rem !important;
}

.remove-button:hover {
  background-color: #c82333 !important;
}

/* RTMP流网格布局 */
.rtmp-grid {
  width: 100%;
  height: 100%;
}

.streams-grid {
  display: grid;
  gap: 10px;
  height: 100%;
  width: 100%;
}

.grid-1 {
  grid-template-columns: 1fr;
  grid-template-rows: 1fr;
}

.grid-2 {
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr;
}

.grid-4 {
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
}

.grid-6 {
  grid-template-columns: 1fr 1fr 1fr;
  grid-template-rows: 1fr 1fr;
}

.grid-9 {
  grid-template-columns: 1fr 1fr 1fr;
  grid-template-rows: 1fr 1fr 1fr;
}

.stream-item {
  border: 1px solid #444;
  border-radius: 4px;
  overflow: hidden;
  background-color: #1a1a1a;
  display: flex;
  flex-direction: column;
}

.stream-header {
  padding: 0.5rem;
  background-color: #333;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #444;
}

.stream-header h4 {
  margin: 0;
  color: #fff;
  font-size: 0.9rem;
}

.stream-status {
  font-size: 0.8rem;
  padding: 0.2rem 0.5rem;
  border-radius: 3px;
  background-color: #666;
  color: #ccc;
}

.stream-status.connected {
  background-color: #28a745;
  color: #fff;
}

.stream-status.error {
  background-color: #dc3545;
  color: #fff;
}

.stream-video {
  flex: 1;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.stream-error, .stream-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #888;
  padding: 1rem;
}

.stream-error p, .stream-loading p {
  margin: 0 0 0.5rem 0;
}

.stream-error small {
  color: #dc3545;
  text-align: center;
}

.no-streams {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #888;
}

</style>