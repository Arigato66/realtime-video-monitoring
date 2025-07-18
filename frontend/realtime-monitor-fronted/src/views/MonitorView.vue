<template>
  <div class="monitor-view-page">
    <!-- 引入顶部栏组件 -->
    <TopBar />
            
    <!-- 页面标题区域 -->
    <div class="page-title">
      <div class="title-content">
        <div class="title-icon">
          <Monitor class="w-8 h-8" />
        </div>
        <div class="title-text">
          <h1>车站实时视频监控系统</h1>
          <p>智能监控 · 实时检测</p>
        </div>
      </div>
      <div class="title-actions">
        <div class="status-indicator" :class="statusIndicatorClass">
          <div class="status-dot"></div>
          <span>{{ statusText }}</span>
        </div>
        <div class="detection-mode-badge">
          <Eye class="w-4 h-4" />
          <span>{{ detectionModeText }}</span>
        </div>
      </div>
    </div>

    <!-- 人脸注册模态框 -->
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

    <!-- RTMP流连接模态框 -->
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

    <!-- 视频区域 -->
    <div class="video-container" :class="{ 'sidebar-visible': isSidebarOpen }">
      <div class="video-wrapper">
        <div class="video-content">
          <transition name="video-fade" mode="out-in">
            <!-- 摄像头实时画面 / RTMP流显示 / 上传文件 (图像) -->
            <div v-if="activeSource === 'webcam' || activeSource === 'rtmp' || (activeSource === 'upload' && isImageUrl(videoSource))" key="image-feed" class="video-frame">
              <img ref="displayImage" :src="videoSource" alt="实时画面" class="webcam-feed" @load="onImageLoad" />
              <div class="video-overlay">
                <div class="recording-indicator">
                  <div class="recording-dot"></div>
                  <span>{{ activeSource === 'rtmp' ? 'RTMP流' : '监控中' }}</span>
                </div>
                <div class="detection-info">
                  <Eye class="w-4 h-4" />
                  <span>{{ detectionModeText }}</span>
                </div>
              </div>
            </div>
            
            <div class="control-panel">
              <h2>控制面板</h2>
              
              <!-- 视频源选择 -->
              <div class="control-section">
                <h3>视频源</h3>
                <div class="button-group">
                  <button @click="connectWebcam" 
                          :class="{ active: activeSource === 'webcam' }" 
                          :disabled="detectionMode === 'face_anti_spoofing'">开启摄像头</button>
                  <button @click="disconnectWebcam" v-if="activeSource === 'webcam'" class="disconnect-button">关闭摄像头</button>
                  <button @click="uploadVideoFile" :disabled="activeSource === 'webcam'">上传视频</button>
            <!-- 上传文件 (视频) -->
            <div v-else-if="activeSource === 'upload' && isVideoUrl(videoSource)" key="upload-video" class="video-frame">
              <video :src="videoSource" controls autoplay class="webcam-feed"></video>
              <div class="video-overlay">
                <div class="file-info">
                  <FileImage class="w-4 h-4" />
                  <span>已上传文件</span>
                </div>
              </div>
            </div>
            
            <!-- 加载状态 -->
            <div v-else-if="activeSource === 'loading'" key="loading" class="loading-state">
              <div class="loading-content">
                <div class="loading-spinner">
                  <Loader2 class="w-8 h-8 animate-spin" />
                </div>
                <p>正在处理文件，请稍候...</p>
                <div class="loading-progress">
                  <div class="progress-bar"></div>
                </div>
              </div>
            </div>
            
            <!-- 默认占位符 -->
            <div v-else key="placeholder" class="video-placeholder">
              <div class="placeholder-content">
                <Monitor class="w-16 h-16 text-gray-400" />
                <h3>开始视频监控</h3>
                <p>请开启摄像头、连接RTMP流或上传文件进行监控</p>
                <div class="quick-actions">
                  <button @click="connectWebcam" class="quick-btn primary">
                    <Video class="w-4 h-4" />
                    <span>开启摄像头</span>
                  </button>
                  <button @click="showRtmpModal" class="quick-btn secondary">
                    <Radio class="w-4 h-4" />
                    <span>RTMP流</span>
                  </button>
                  <button @click="uploadVideoFile" class="quick-btn tertiary">
                    <Upload class="w-4 h-4" />
                    <span>上传文件</span>
                  </button>
                </div>
                <!-- 活体检测按钮单独一行 -->
                <div class="button-group liveness-button-group">
                  <button 
                    @click="toggleFaceAntiSpoofing" 
                    
                    :class="{ active: detectionMode === 'face_anti_spoofing', 'liveness-button': true }"
                    data-mode="face_anti_spoofing">
                    活体检测
                  </button>
                </div>
              </div>
               <!-- 在检测模式和危险区域设置之间插入 -->
              <div class="control-section">
                <div class="scream-status-bar">
                  <span>尖叫声检测状态：{{ screamStatus }}</span>
                  <button v-if="!screamDetecting" @click="startScreamDetection">开启尖叫声检测</button>
                  <button v-else @click="stopScreamDetection">关闭尖叫声检测</button>
                  <div class="scream-volume-bar">
                    <div class="scream-volume-inner" :style="{width: (screamVolume*100).toFixed(0)+'%', background: screamVolume > 0.5 ? '#f44336' : screamVolume > 0.2 ? '#ffc107' : '#4caf50'}"></div>
                  </div>
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
          </transition>
        </div>
        
        <!-- 危险区域编辑/实时检测绘制Canvas -->
        <canvas v-if="editMode || activeSource === 'rtmp'" 
                ref="interactionCanvas" 
                class="interaction-canvas"
                @mousedown="handleMouseDown"
                @mousemove="handleMouseMove"
                @mouseup="handleMouseUp"
                @mouseleave="handleMouseLeave"
                @dblclick="handleDoubleClick"
                @contextmenu.prevent="handleRightClick">
        </canvas>
      </div>
    </div>

    <!-- 可滑动侧边栏控制面板 -->
    <aside class="control-sidebar" :class="{ 'sidebar-open': isSidebarOpen }">
      <div class="sidebar-header">
        <div class="header-content">
          <Settings class="w-5 h-5" />
          <h2>控制面板</h2>
        </div>
        <div class="header-actions">
          <button @click="toggleSidebar" class="close-btn">
            <X class="w-4 h-4" />
          </button>
        </div>
      </div>
      <div class="sidebar-content">
        <!-- 视频源控制 -->
        <div class="control-section">
          <div class="section-header">
            <PlayCircle class="w-4 h-4" />
            <h3>视频源控制</h3>
          </div>
          <div class="video-controls">
            <button 
              @click="connectWebcam"
              :class="{ active: activeSource === 'webcam' }"
              class="control-btn primary"
            >
              <Video class="w-4 h-4" />
              <span>{{ activeSource === 'webcam' ? '摄像头运行中' : '开启摄像头' }}</span>
            </button>
            <button 
              @click="disconnectWebcam"
              v-if="activeSource === 'webcam'"
              class="control-btn danger"
            >
              <Square class="w-4 h-4" />
              <span>停止摄像头</span>
            </button>
            <button 
              @click="showRtmpModal"
              :disabled="activeSource === 'webcam'"
              class="control-btn secondary"
            >
              <Radio class="w-4 h-4" />
              <span>RTMP流连接</span>
            </button>
            <button 
              @click="uploadVideoFile"
              :disabled="activeSource === 'webcam'"
              class="control-btn tertiary"
            >
              <Upload class="w-4 h-4" />
              <span>上传文件</span>
            </button>
          </div>
        </div>

        <!-- 检测模式选择 -->
        <div class="control-section">
          <div class="section-header">
            <Eye class="w-4 h-4" />
            <h3>检测模式</h3>
            <div class="mode-indicator">{{ detectionModeText }}</div>
          </div>
          <div class="detection-modes-grid">
            <button 
              @click="setDetectionMode('object_detection')" 
              :class="{ active: detectionMode === 'object_detection' }"
              class="mode-btn"
            >
              <Target class="w-4 h-4" />
              <span>目标检测</span>
            </button>
            <button 
              @click="setDetectionMode('face_only')" 
              :class="{ active: detectionMode === 'face_only' }"
              class="mode-btn"
            >
              <User class="w-4 h-4" />
              <span>人脸识别</span>
            </button>
            <button 
              @click="setDetectionMode('fall_detection')" 
              :class="{ active: detectionMode === 'fall_detection' }"
              class="mode-btn"
            >
              <AlertTriangle class="w-4 h-4" />
              <span>跌倒检测</span>
            </button>
            <button 
              @click="setDetectionMode('smoking_detection')" 
              :class="{ active: detectionMode === 'smoking_detection' }"
              class="mode-btn"
            >
              <Cigarette class="w-4 h-4" />
              <span>抽烟检测</span>
            </button>
            <button 
              @click="setDetectionMode('violence_detection')" 
              :class="{ active: detectionMode === 'violence_detection' }"
              class="mode-btn"
            >
              <Shield class="w-4 h-4" />
              <span>暴力检测</span>
            </button>
          </div>
        </div>

        <!-- 危险区域设置 -->
        <div class="control-section">
          <div class="section-header">
            <MapPin class="w-4 h-4" />
            <h3>危险区域设置</h3>
            <div v-if="editMode" class="edit-badge">编辑中</div>
          </div>
          <div class="zone-controls">
            <button @click="toggleEditMode" :class="{ active: editMode }" class="control-btn primary">
              <Edit class="w-4 h-4" />
              <span>{{ editMode ? '保存区域' : '编辑区域' }}</span>
            </button>
            <button v-if="editMode" @click="cancelEdit" class="control-btn secondary">
              <X class="w-4 h-4" />
              <span>取消编辑</span>
            </button>
          </div>
          <div v-if="editMode" class="edit-instructions">
            <div class="instruction-item">
              <MousePointer class="w-3 h-3" />
              <span>点击并拖动区域点以调整位置</span>
            </div>
            <div class="instruction-item">
              <MousePointer2 class="w-3 h-3" />
              <span>右键点击删除点</span>
            </div>
            <div class="instruction-item">
              <Plus class="w-3 h-3" />
              <span>双击添加新点</span>
            </div>
          </div>
        </div>

        <!-- 参数设置 -->
        <div class="control-section">
          <div class="section-header">
            <Sliders class="w-4 h-4" />
            <h3>参数设置</h3>
          </div>
          <div class="settings-grid">
            <div class="setting-item">
              <div class="setting-header">
                <label>安全距离</label>
                <span class="setting-value">{{ safetyDistance }}px</span>
              </div>
              <input type="range" v-model="safetyDistance" min="10" max="200" step="5" class="setting-slider" />
            </div>
            <div class="setting-item">
              <div class="setting-header">
                <label>警报阈值</label>
                <span class="setting-value">{{ loiteringThreshold }}s</span>
              </div>
              <input type="range" v-model="loiteringThreshold" min="0.5" max="10" step="0.5" class="setting-slider" />
            </div>
          </div>
          <button @click="updateSettings" class="apply-settings-btn">
            <Check class="w-4 h-4" />
            <span>应用设置</span>
          </button>
        </div>

        <!-- 人员管理 -->
        <div class="control-section">
          <div class="section-header">
            <Users class="w-4 h-4" />
            <h3>人员管理</h3>
            <div class="user-count">{{ registeredUsers.length }}</div>
          </div>
          
          <div class="user-management">
            <button @click="registerFace" class="add-user-btn">
              <UserPlus class="w-4 h-4" />
              <span>添加新人员</span>
            </button>
            
            <div class="search-box">
              <Search class="w-4 h-4 search-icon" />
              <input 
                v-model="searchQuery"
                type="text"
                placeholder="搜索人员..."
                class="search-input"
              />
            </div>
          </div>
          
          <div class="user-list-container">
            <transition-group name="user-list" tag="ul" class="user-list">
              <li
                v-for="user in filteredUsers"
                :key="user"
                class="user-item"
              >
                <div class="user-info">
                  <div class="user-avatar">
                    <User class="w-4 h-4" />
                  </div>
                  <div class="user-details">
                    <span class="user-name">{{ user }}</span>
                    <span class="user-status">已注册人员</span>
                  </div>
                </div>
                <div class="user-actions">
                  <button @click="deleteFace(user)" class="action-btn delete">
                    <Trash2 class="w-3 h-3" />
                  </button>
                </div>
              </li>
            </transition-group>
            <div v-if="filteredUsers.length === 0" class="empty-state">
              <UserX class="w-8 h-8 text-gray-400" />
              <p>{{ searchQuery ? '未找到匹配的人员' : '未注册任何人员' }}</p>
            </div>
          </div>
        </div>

        <!-- RTMP流管理 -->
        <div class="control-section">
          <div class="section-header">
            <Radio class="w-4 h-4" />
            <h3>活动RTMP流</h3>
            <div class="stream-count">{{ filteredRtmpStreams.length }}</div>
          </div>
          <div class="search-box mb-4">
            <Search class="w-4 h-4 search-icon" />
            <input 
              v-model="searchRtmpQuery"
              type="text"
              placeholder="搜索RTMP流..."
              class="search-input"
            />
          </div>
          <div class="stream-list">
            <template v-if="filteredRtmpStreams.length > 0">
              <div v-for="stream in filteredRtmpStreams" :key="stream.stream_id" class="stream-item">
                <div class="stream-info">
                  <div class="stream-header">
                    <h4>{{ stream.name }}</h4>
                    <span class="stream-status" :class="stream.status">{{ stream.status }}</span>
                  </div>
                  <p class="stream-url">{{ stream.rtmp_url }}</p>
                </div>
                <div class="stream-controls">
                  <button @click="selectRtmpStream(stream.stream_id)" 
                          class="stream-btn select" 
                          :class="{ active: currentRtmpStream === stream.stream_id }">
                    <Play class="w-3 h-3" />
                  </button>
                  <button @click="stopRtmpStream(stream.stream_id)" class="stream-btn stop">
                    <Square class="w-3 h-3" />
                  </button>
                  <button @click="deleteRtmpStream(stream.stream_id)" class="stream-btn delete">
                    <Trash2 class="w-3 h-3" />
                  </button>
                </div>
              </div>
            </template>
            <div v-else class="empty-state">
              <Radio class="w-8 h-8 text-gray-400" />
              <p>{{ searchRtmpQuery ? '未找到匹配的RTMP流' : '当前暂无RTMP流信息' }}</p>
            </div>
          </div>
        </div>

        <!-- 告警信息 -->
        <div class="control-section">
          <div class="section-header">
            <AlertTriangle class="w-4 h-4" />
            <h3>告警信息</h3>
            <div v-if="alerts.length > 0" class="alert-badge">
              {{ alerts.length }}
            </div>
          </div>
          <div class="alerts-container" :class="{ 'has-alerts': alerts.length > 0 }">
            <transition-group name="alert-list" tag="div" class="alert-list">
              <div
                v-for="(alert, index) in alerts"
                :key="`alert-${index}`"
                class="alert-item"
              >
                <div class="alert-header">
                  <AlertCircle class="w-3 h-3" />
                  <span class="alert-time">{{ formatTime(new Date()) }}</span>
                </div>
                <p class="alert-message">{{ alert }}</p>
              </div>
            </transition-group>
            <div v-if="alerts.length === 0" class="empty-state">
              <Shield class="w-8 h-8 text-gray-400" />
              <p>当前无告警信息</p>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- 可拖动悬浮按钮 -->
    <div 
      class="floating-control"
      :style="floatingButtonStyle"
      @mousedown="startFloatingDrag"
      @touchstart="startFloatingDrag"
    >
      <button
        class="sidebar-toggle-btn"
        @click.stop="toggleSidebar"
        :class="{ 'sidebar-open': isSidebarOpen }"
      >
        <transition name="icon-rotate" mode="out-in">
          <ChevronLeft v-if="isSidebarOpen" key="close" class="w-5 h-5" />
          <Settings v-else key="open" class="w-5 h-5" />
        </transition>
      </button>
    </div>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { ref, onMounted, onUnmounted, nextTick, computed, reactive } from 'vue'
import io from 'socket.io-client'
import TopBar from '../components/TopBar.vue'

// 导入图标
import {
  Monitor, Video, Upload, Square, Settings, ChevronLeft, X, PlayCircle,
  AlertTriangle, AlertCircle, Shield, Users, UserPlus, User, UserX, Trash2,
  FileImage, Loader2, Eye, Search, Target, Edit, MapPin, Sliders, Check,
  MousePointer, MousePointer2, Plus, Radio, Play, Cigarette
} from 'lucide-vue-next'

// 路由和状态变量
const route = useRoute()
const windowWidth = ref(window.innerWidth)
const isSidebarOpen = ref(windowWidth.value >= 992)

// 悬浮按钮相关
const floatingButton = reactive({
  x: 24,
  y: 120,
  isDragging: false,
  offsetX: 0,
  offsetY: 0
})

// API端点设置
const SERVER_ROOT_URL = 'http://localhost:5000'
const API_BASE_URL = `${SERVER_ROOT_URL}/api`
const DLIB_API_BASE_URL = `${API_BASE_URL}/dlib`
const VIDEO_FEED_URL = `${API_BASE_URL}/video_feed`

// 人脸注册模态框状态
const showRegistrationModal = ref(false)
const registrationStatus = ref('')
const registrationName = ref('')
const capturedFramesCount = ref(0)
const registrationVideoEl = ref(null)
const registrationSocket = ref(null)
const localStream = ref(null)
const wasWebcamActive = ref(false)

// 状态变量
const videoSource = ref('')
const activeSource = ref('')
const editMode = ref(false)
const alerts = ref([])
const safetyDistance = ref(100)
const loiteringThreshold = ref(2.0)
const detectionMode = ref('object_detection') // 新增：检测模式状态
const originalDangerZone = ref(null)
// const fileInput = ref(null) // No longer needed
const faceFileInput = ref(null) // 用于人脸注册的文件输入
const registeredUsers = ref([]) // 已注册用户列表
const pollingIntervalId = ref(null) // 用于轮询的定时器ID
const videoTaskId = ref(''); // 保存当前视频处理任务的ID
const webcamImg = ref(null);
const screamStatus = ref('未开启');
const screamDetecting = ref(false);
let screamSocket = null;
const screamVolume = ref(0);

function startScreamDetection() {
  if (screamSocket) return;
  screamSocket = io(`${SERVER_ROOT_URL}/api/scream_ws`);
  screamSocket.on('connect', () => {
    screamSocket.emit('scream_detect', { action: 'start' });
    screamStatus.value = '正在监听...';
    screamDetecting.value = true;
  });
  screamSocket.on('scream_status', (data) => {
    if (data.volume !== undefined) screamVolume.value = data.volume;
    if (data.status === 'scream') {
      screamStatus.value = '🚨 检测到尖叫声！';
    } else if (data.status === 'normal') {
      screamStatus.value = '✅ 无尖叫';
    } else if (data.status === 'listening') {
      screamStatus.value = '正在监听...';
    } else if (data.status === 'stopped') {
      screamStatus.value = '已停止';
      screamDetecting.value = false;
    }
  });
  screamSocket.on('scream_alert', (data) => {
    alerts.value.unshift(data.alert);
  });
  screamSocket.on('disconnect', () => {
    screamStatus.value = '已断开';
    screamDetecting.value = false;
    screamSocket = null;
  });
const detectionMode = ref('object_detection')
const originalDangerZone = ref([])
const registeredUsers = ref([])
const pollingIntervalId = ref(null)
const videoTaskId = ref('')
const searchQuery = ref('')
const displayImage = ref(null)

// Canvas 和危险区域状态
const interactionCanvas = ref(null)
const dangerZone = ref([])
const isDragging = ref(false)
const draggingIndex = ref(-1)

// RTMP相关状态
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
const currentDetections = ref([]) // For RTMP stream detections
const searchRtmpQuery = ref('') // New: for RTMP stream search
const rtmpListPollingIntervalId = ref(null) // New: for polling RTMP stream list

// Computed properties
const statusIndicatorClass = computed(() => ({
  active: activeSource.value === 'webcam' || activeSource.value === 'rtmp'
}))

const statusText = computed(() => {
  switch (activeSource.value) {
    case 'webcam': return '摄像头监控中'
    case 'rtmp': return 'RTMP流监控中'
    case 'upload': return '文件分析中'
    default: return '监控已停止'
  }
})

const detectionModeText = computed(() => {
  const modes = {
    'object_detection': '目标检测',
    'face_only': '人脸识别',
    'fall_detection': '跌倒检测',
    'smoking_detection': '抽烟检测',
    'violence_detection': '暴力检测'
  }
  return modes[detectionMode.value] || '未知模式'
})

const floatingButtonStyle = computed(() => ({
  left: `${floatingButton.x}px`,
  top: `${floatingButton.y}px`,
  cursor: floatingButton.isDragging ? 'grabbing' : 'grab'
}))

const filteredUsers = computed(() => {
  if (!searchQuery.value) return registeredUsers.value
  return registeredUsers.value.filter(user =>
    user.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

const filteredRtmpStreams = computed(() => { // New: Filtered RTMP streams
  if (!searchRtmpQuery.value) return activeStreams.value
  return activeStreams.value.filter(stream =>
    stream.name.toLowerCase().includes(searchRtmpQuery.value.toLowerCase())
  )
})

// Time formatting function
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

// Helper to stop media stream
const stopStream = (stream) => {
  if (stream && stream.getTracks) {
    stream.getTracks().forEach(track => track.stop())
  }
}

function stopScreamDetection() {
  if (screamSocket) {
    screamSocket.emit('scream_detect', { action: 'stop' });
    screamSocket.disconnect();
    screamSocket = null;
    screamStatus.value = '已停止';
    screamDetecting.value = false;
  }
}
// --- API 调用封装 ---
// 使用新的 DLIB_API_BASE_URL
const dlibApiFetch = async (endpoint, options = {}) => {
  try {
    const response = await fetch(`${DLIB_API_BASE_URL}${endpoint}`, options)
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: response.statusText }))
      throw new Error(errorData.message || `服务器错误: ${response.status}`)
    }
    return await response.json()
  } catch (error) {
    console.error(`Dlib API调用失败 ${endpoint}:`, error)
    alert(`操作失败: ${error.message}`)
    throw error
  }
}

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

// --- 检查人脸识别按钮状态的函数 ---
const checkFaceRecognitionStatus = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/face_recognition_status`);
    const data = await response.json();
    return data.enabled;
  } catch (error) {
    console.error("获取人脸识别状态失败:", error);
    return false;
  }
};

// --- 检测模式管理 ---
const loadDetectionMode = async () => {
  try {
    const data = await apiFetch('/detection_mode')
    detectionMode.value = data.mode
    console.log('Detection mode loaded:', data.mode)
  } catch (error) {
    // Error handled by apiFetch
  }
}

// 在setDetectionMode函数中添加活体检测的处理
const setDetectionMode = async (mode) => {
  if (detectionMode.value === mode) return; // 如果模式未变，则不执行任何操作
  
  // 如果是人脸识别模式，先检查是否启用
  if (mode === 'face_only') {
    const enabled = await checkFaceRecognitionStatus();
    if (!enabled) {
      alert('请先通过活体检测后才能使用人脸识别功能');
      return;
    }
  }
  

  if (detectionMode.value === mode) return
  try {
    const data = await apiFetch('/detection_mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: mode })
    })
    detectionMode.value = mode
    
    const modeNames = {
      'object_detection': '目标检测',
      'face_only': '人脸识别',
      'fall_detection': '跌倒检测',
      'smoking_detection': '抽烟检测',
      'violence_detection': '暴力检测',
      'face_anti_spoofing': '活体检测'
    };
    alert(`检测模式已切换为: ${modeNames[mode] || mode}`);

    // 如果是活体检测模式，启动活体检测服务
    if (mode === 'face_anti_spoofing') {
      startFaceAntiSpoofing();
    }

    console.log(data.message);

      'violence_detection': '暴力检测'
    }
    alert(`检测模式已切换为: ${modeNames[mode] || mode}`)
    console.log(data.message)
  } catch (error) {
    // Error handled by apiFetch
  }
}

// 添加启动活体检测的函数
const startFaceAntiSpoofing = async () => {
  try {
    // 禁用按钮，防止重复点击
    const faceAntiSpoofingButton = document.querySelector('button[data-mode="face_anti_spoofing"]');
    if (faceAntiSpoofingButton) {
      faceAntiSpoofingButton.disabled = true;
      setTimeout(() => {
        faceAntiSpoofingButton.disabled = false;
      }, 3000); // 3秒后恢复按钮
    }
    
    const data = await apiFetch('/start_face_anti_spoofing', {
      method: 'POST'
    });
    
    if (data.status === 'warning') {
      console.log(data.message);
      alert('活体检测已经在运行中，请勿重复启动');
    } else {
      console.log(data.message);
    }
  } catch (error) {
    // apiFetch中已处理错误
  }
};

// 新增：切换活体检测模式
const toggleFaceAntiSpoofing = async () => {
  if (detectionMode.value === 'face_anti_spoofing') {
    // 如果当前是活体检测模式，切换回目标检测模式
    await setDetectionMode('object_detection');
  } else {
    // 如果当前不是活体检测模式，切换到活体检测模式
    await setDetectionMode('face_anti_spoofing');
    // 启动活体检测
    startFaceAntiSpoofing();
  }
};


// --- 配置管理 ---
const loadConfig = async () => {
  try {
    const data = await apiFetch('/config')
    safetyDistance.value = data.safety_distance
    loiteringThreshold.value = data.loitering_threshold
    dangerZone.value = data.danger_zone || []
    originalDangerZone.value = JSON.parse(JSON.stringify(dangerZone.value))
    console.log('Configuration loaded:', data)
  } catch (error) {
    // Error handled by apiFetch
  }
}

const updateSettings = async () => {
  try {
    const data = await apiFetch('/update_thresholds', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        safety_distance: parseInt(safetyDistance.value),
        loitering_threshold: parseFloat(loiteringThreshold.value)
      })
    })
    alert(data.message)
  } catch (error) {
    // Error handled by apiFetch
  }
}

// --- 人脸管理 (已更新为 Dlib API) ---
const loadRegisteredUsers = async () => {
  try {
    const data = await dlibApiFetch('/faces')
    registeredUsers.value = data.names
  } catch (error) {
    // Error handled by dlibApiFetch
  }
}

const deleteFace = async (name) => {
  if (confirm(`确定要删除人员 '${name}' 吗?`)) {
    try {
      const data = await dlibApiFetch(`/faces/${name}`, { method: 'DELETE' })
      alert(data.message)
      loadRegisteredUsers()
    } catch (error) {
      // Error handled by dlibApiFetch
    }
  }
}

// --- 新的交互式注册流程 ---
const registerFace = () => {
  const name = prompt("请输入要注册人员的姓名:")
  if (name && name.trim()) {
    if (activeSource.value === 'webcam') {
      wasWebcamActive.value = true
      disconnectWebcam()
    } else {
      wasWebcamActive.value = false
    }
    
    registrationName.value = name.trim()
    showRegistrationModal.value = true
    capturedFramesCount.value = 0
    registrationStatus.value = '准备中...'
    
    nextTick(() => {
      setTimeout(() => {
        startRegistrationCapture()
      }, 500)
    })
  }
}

const startRegistrationCapture = async () => {
  if (!registrationVideoEl.value) {
    console.error("注册视频元素尚未准备好。")
    registrationStatus.value = '错误：无法访问视频元素。'
    return
  }

  try {
    localStream.value = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
    registrationVideoEl.value.srcObject = localStream.value
  } catch(err) {
    console.error("无法访问摄像头:", err)
    registrationStatus.value = '错误：无法访问摄像头。'
    alert('无法访问摄像头，请检查权限。')
    closeRegistrationModal()
    return
  }

  registrationSocket.value = io(`${SERVER_ROOT_URL}/dlib/register`)
  
  registrationSocket.value.on('connect', () => {
    console.log('已连接到注册 WebSocket')
    registrationStatus.value = '连接成功，正在开始...'
    registrationSocket.value.emit('start_registration', { name: registrationName.value })
  })

  registrationSocket.value.on('status', (data) => {
    console.log('注册状态:', data.message)
    registrationStatus.value = data.message
  })

  registrationSocket.value.on('capture_result', (data) => {
    if (data.status === 'success') {
      capturedFramesCount.value = data.count
      registrationStatus.value = `成功捕获 ${data.count} 帧`
    } else {
      registrationStatus.value = `捕获失败: ${data.message}`
    }
  })

  registrationSocket.value.on('error', (data) => {
    console.error('注册 WebSocket 错误:', data.message)
    registrationStatus.value = `错误: ${data.message}`
  })

  registrationSocket.value.on('disconnect', () => {
    console.log('已从注册 WebSocket断开')
    registrationStatus.value = '连接已断开。'
  })
}

const captureFrame = () => {
  if (!registrationVideoEl.value || !registrationSocket.value) return
  
  const canvas = document.createElement('canvas')
  canvas.width = registrationVideoEl.value.videoWidth
  canvas.height = registrationVideoEl.value.videoHeight
  const context = canvas.getContext('2d')
  context.drawImage(registrationVideoEl.value, 0, 0, canvas.width, canvas.height)
  
  const imageData = canvas.toDataURL('image/jpeg')
  
  registrationSocket.value.emit('frame_for_capture', { image: imageData })
  registrationStatus.value = '已发送捕获请求...'
}

// 在关闭模态框时停止视频流
const closeRegistrationModal = (isUnmounting = false) => {
  showRegistrationModal.value = false
  registrationName.value = ''
  registrationStatus.value = ''
  capturedFramesCount.value = 0
  
  if (localStream.value && localStream.value.getTracks) {
    localStream.value.getTracks().forEach(track => track.stop())
    localStream.value = null
  }
  
  if (registrationSocket.value) {
    registrationSocket.value.disconnect()
    registrationSocket.value = null
  }
  
  if (!isUnmounting && wasWebcamActive.value) {
    connectWebcam()
    wasWebcamActive.value = false
  }
  
  loadRegisteredUsers()
}


// --- 视频/图像处理 ---
const connectWebcam = () => {
  stopPolling()
  stopRtmpListPolling(); // Stop RTMP list polling when webcam connects
  if (rtmpSocket.value) { // Disconnect RTMP socket if active
    rtmpSocket.value.disconnect();
    
    rtmpSocket.value = null;
  }
  currentDetections.value = []; // Clear detections
  activeSource.value = 'webcam'
  nextTick(() => {
    if (displayImage.value) {
      displayImage.value.src = `${VIDEO_FEED_URL}?t=${new Date().getTime()}`
    }
    drawCanvas(); // Redraw canvas for danger zones
  })
  videoSource.value = `${VIDEO_FEED_URL}?t=${new Date().getTime()}`
  startAlertPolling()
}

const disconnectWebcam = async () => {
  if (activeSource.value !== 'webcam') return
  try {
    await fetch(`${API_BASE_URL}/stop_video_feed`, { method: 'POST' })
    console.log("已向后端发送停止摄像头指令。")
  } catch (error) {
    console.error("发送停止指令失败:", error)
  } finally {
    activeSource.value = ''
    videoSource.value = ''
    currentDetections.value = []; // Clear detections
    stopAlertPolling()
    drawCanvas(); // Clear canvas
    startRtmpListPolling(); // Restart RTMP list polling
  }
}

const uploadVideoFile = () => {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'video/mp4,image/jpeg,image/jpg'
  input.onchange = handleFileUpload
  input.click()
}

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  stopPolling()
  stopRtmpListPolling(); // Stop RTMP list polling when uploading file
  if (rtmpSocket.value) { // Disconnect RTMP socket if active
    rtmpSocket.value.disconnect();
    rtmpSocket.value = null;
  }
  currentDetections.value = []; // Clear detections
  videoSource.value = ''
  activeSource.value = 'loading'

  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      body: formData
    })

    if (response.status === 202) {
      const data = await response.json()
      videoTaskId.value = data.task_id
      startPolling(data.task_id)
    } else if (response.ok) {
      const data = await response.json()
      videoSource.value = `${SERVER_ROOT_URL}${data.file_url}?t=${new Date().getTime()}`
      activeSource.value = 'upload'
      alerts.value = data.alerts || []
      stopAlertPolling()
      nextTick(() => {
        drawCanvas(); // Redraw canvas for danger zones
      });
    } else {
      const errorData = await response.json()
      throw new Error(errorData.message || '文件上传失败')
    }
  } catch (error) {
    activeSource.value = ''
    alert(error.message || '操作失败')
    currentDetections.value = []; // Clear detections
    drawCanvas(); // Clear canvas
    startRtmpListPolling(); // Restart RTMP list polling
  }
}

// Polling methods
const startPolling = (taskId) => {
  pollingIntervalId.value = setInterval(() => {
    pollTaskStatus(taskId)
  }, 2000)
}

const stopPolling = () => {
  if (pollingIntervalId.value) {
    clearInterval(pollingIntervalId.value)
    pollingIntervalId.value = null
    videoTaskId.value = ''
  }
}

const pollTaskStatus = async (taskId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/video/task_status/${taskId}`)
    
    if (response.status === 200) {
      stopPolling()
      const data = await response.json()
      videoSource.value = `${SERVER_ROOT_URL}${data.file_url}?t=${new Date().getTime()}`
      activeSource.value = 'upload'
      alerts.value = data.alerts || []
      nextTick(() => {
        drawCanvas(); // Redraw canvas for danger zones
      });
    } else if (response.status === 202) {
      console.log('视频处理中...')
    } else {
      stopPolling()
      const errorData = await response.json()
      throw new Error(errorData.message || '视频处理失败')
    }
  } catch (error) {
    stopPolling()
    activeSource.value = ''
    currentDetections.value = []; // Clear detections
    drawCanvas(); // Clear canvas
    alert(error.message)
  }
}


// --- V3: 混合驱动的危险区域编辑 ---

// 核心绘制函数
const drawCanvas = () => {
  const canvas = interactionCanvas.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height) // Always clear

  if (editMode.value) {
    // Draw danger zone
    if (dangerZone.value.length < 2) return

    ctx.beginPath()
    ctx.moveTo(dangerZone.value[0][0], dangerZone.value[0][1])
    for (let i = 1; i < dangerZone.value.length; i++) {
      ctx.lineTo(dangerZone.value[i][0], dangerZone.value[i][1])
    }
    ctx.closePath()
    
    ctx.fillStyle = 'rgba(255, 0, 0, 0.3)'
    ctx.fill()
    ctx.strokeStyle = '#FF0000'
    ctx.lineWidth = 2
    ctx.stroke()

    ctx.fillStyle = '#FF0000'
    dangerZone.value.forEach(point => {
      ctx.beginPath()
      ctx.arc(point[0], point[1], 8, 0, Math.PI * 2)
      ctx.fill()
    })
  } else if (activeSource.value === 'rtmp' && currentDetections.value.length > 0) {
    // Draw detections for RTMP stream if not in edit mode
    drawDetections();
  }
}

const drawDetections = () => {
  const canvas = interactionCanvas.value;
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  // Clear only the detection layer if not in edit mode (drawCanvas handles full clear in edit mode)
  if (!editMode.value) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

  currentDetections.value.forEach(detection => {
    if (detection.type === 'bbox' && detection.box) {
      const [x1, y1, x2, y2] = detection.box;
      ctx.strokeStyle = detection.color || '#00FF00'; // Default green
      ctx.lineWidth = 2;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
      if (detection.label) {
        ctx.fillStyle = detection.color || '#00FF00';
        ctx.font = '16px Arial';
        ctx.fillText(detection.label, x1, y1 > 10 ? y1 - 5 : y1 + 15);
      }
    } else if (detection.type === 'polygon' && detection.points) {
      ctx.strokeStyle = detection.color || '#FFFF00'; // Default yellow for polygons
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(detection.points[0][0], detection.points[0][1]);
      for (let i = 1; i < detection.points.length; i++) {
        ctx.lineTo(detection.points[i][0], detection.points[i][1]);
      }
      ctx.closePath();
      ctx.stroke();
    }
    // Add other detection types as needed
  });
};

const onImageLoad = () => {
  nextTick(() => {
    const img = displayImage.value
    const canvas = interactionCanvas.value
    if (img && canvas) {
      // Set canvas dimensions to match the natural size of the image
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      // Set canvas style dimensions to match the displayed size of the image
      canvas.style.width = `${img.clientWidth}px`
      canvas.style.height = `${img.clientHeight}px`
      drawCanvas() // Redraw danger zones or detections
    }
  })
}

const toggleEditMode = async () => {
  if (!editMode.value) {
    try {
      await apiFetch('/toggle_edit_mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ edit_mode: true })
      })
      
      await loadConfig()
      editMode.value = true
      currentDetections.value = []; // Clear detections when entering edit mode
      nextTick(() => {
        onImageLoad()
      })
    } catch (error) {
      console.error('进入编辑模式失败:', error)
      alert('无法进入编辑模式，请重试。')
    }
  } else {
    try {
      await apiFetch('/update_danger_zone', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ danger_zone: dangerZone.value }),
      })
      
      await apiFetch('/toggle_edit_mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ edit_mode: false })
      })
      
      editMode.value = false
      alert('危险区域已成功保存！')

      // Force refresh video feed to show updated area
      if (activeSource.value === 'webcam') {
        videoSource.value = `${VIDEO_FEED_URL}?t=${new Date().getTime()}`
      } else if (activeSource.value === 'rtmp' && currentRtmpStream.value) {
        videoSource.value = `${API_BASE_URL}/streams/${currentRtmpStream.value}/feed?t=${new Date().getTime()}`
      }
      nextTick(() => {
        drawCanvas(); // Clear canvas or redraw based on new state
      });
    } catch (error) {
      console.error('保存危险区域失败:', error)
      alert('保存危险区域失败，请重试。')
    }
  }
}

const cancelEdit = async () => {
  try {
    await apiFetch('/toggle_edit_mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ edit_mode: false })
    })
    editMode.value = false
    dangerZone.value = JSON.parse(JSON.stringify(originalDangerZone.value)); // Revert to original
    nextTick(() => {
      drawCanvas(); // Redraw with original danger zone
    });
  } catch (error) {
    console.error('取消编辑失败:', error)
    alert('取消编辑操作失败。')
  }
}

// Canvas interaction event handlers
const getMouseCoords = (event) => {
  const canvas = interactionCanvas.value
  if (!canvas) return null

  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height

  const x = (event.clientX - rect.left) * scaleX
  const y = (event.clientY - rect.top) * scaleY

  return { x, y }
}

const handleMouseDown = (event) => {
  if (!editMode.value) return
  const coords = getMouseCoords(event)
  if (!coords) return

  for (let i = 0; i < dangerZone.value.length; i++) {
    const point = dangerZone.value[i]
    const distance = Math.sqrt(Math.pow(coords.x - point[0], 2) + Math.pow(coords.y - point[1], 2))
    if (distance < 10) {
      isDragging.value = true
      draggingIndex.value = i
      return
    }
  }
}

const handleMouseMove = (event) => {
  if (!isDragging.value || draggingIndex.value === -1) return
  let coords = getMouseCoords(event)
  if (!coords) return
  
  const canvas = interactionCanvas.value
  coords.x = Math.max(0, Math.min(coords.x, canvas.width))
  coords.y = Math.max(0, Math.min(coords.y, canvas.height))
  
  dangerZone.value[draggingIndex.value] = [coords.x, coords.y]
  drawCanvas()
}

const handleMouseUp = () => {
  isDragging.value = false
  draggingIndex.value = -1
}

const handleMouseLeave = () => {
  if (isDragging.value) {
    isDragging.value = false
    draggingIndex.value = -1
  }
}

const handleDoubleClick = (event) => {
  if (!editMode.value) return
  let coords = getMouseCoords(event)
  if (!coords) return
  
  const canvas = interactionCanvas.value
  coords.x = Math.max(0, Math.min(coords.x, canvas.width))
  coords.y = Math.max(0, Math.min(coords.y, canvas.height))

  dangerZone.value.push([coords.x, coords.y])
  drawCanvas()
}

const handleRightClick = (event) => {
  if (!editMode.value) return
  const coords = getMouseCoords(event)
  if (!coords) return
  
  for (let i = dangerZone.value.length - 1; i >= 0; i--) {
    const point = dangerZone.value[i]
    const distance = Math.sqrt(Math.pow(coords.x - point[0], 2) + Math.pow(coords.y - point[1], 2))
    if (distance < 10) {
      dangerZone.value.splice(i, 1)
      drawCanvas()
      return
    }
  }
}

// Floating button drag control
const startFloatingDrag = (e) => {
  e.preventDefault()
  const touchEvent = e.touches?.[0] || e
  const rect = e.currentTarget.getBoundingClientRect()
  
  floatingButton.isDragging = true
  floatingButton.offsetX = touchEvent.clientX - rect.left
  floatingButton.offsetY = touchEvent.clientY - rect.top
  
  document.addEventListener('mousemove', handleFloatingDrag)
  document.addEventListener('mouseup', stopFloatingDrag)
  document.addEventListener('touchmove', handleFloatingDrag, { passive: false })
  document.addEventListener('touchend', stopFloatingDrag)
}

const handleFloatingDrag = (e) => {
  if (!floatingButton.isDragging) return
  
  const touchEvent = e.touches?.[0] || e
  
  let newX = touchEvent.clientX - floatingButton.offsetX
  let newY = touchEvent.clientY - floatingButton.offsetY
  
  const buttonWidth = 48
  const buttonHeight = 48
  const maxX = window.innerWidth - buttonWidth
  const maxY = window.innerHeight - buttonHeight
  
  newX = Math.max(0, Math.min(newX, maxX))
  newY = Math.max(0, Math.min(newY, maxY))
  
  floatingButton.x = newX
  floatingButton.y = newY
}

const stopFloatingDrag = () => {
  floatingButton.isDragging = false
  document.removeEventListener('mousemove', handleFloatingDrag)
  document.removeEventListener('mouseup', stopFloatingDrag)
  document.removeEventListener('touchmove', handleFloatingDrag)
  document.removeEventListener('touchend', stopFloatingDrag)
}

// RTMP stream management
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
      
      // Start stream processing
      await startRtmpStream(data.stream_id)
      
      // Refresh stream list
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
  stopPolling(); // Stop any file polling
  stopAlertPolling(); // Stop alert polling as RTMP socket will provide detections
  if (activeSource.value === 'webcam') { // Disconnect webcam if active
    disconnectWebcam();
  }
  // Disconnect existing RTMP socket if any, before connecting to a new one
  if (rtmpSocket.value) {
    rtmpSocket.value.disconnect();
  }

  currentRtmpStream.value = streamId
  activeSource.value = 'rtmp'
  videoSource.value = `${API_BASE_URL}/streams/${streamId}/feed?t=${new Date().getTime()}`
  currentDetections.value = []; // Clear previous detections
  
  // Start receiving detections for this stream
  connectToRtmpSocket(streamId)
  nextTick(() => {
    onImageLoad(); // Ensure canvas is sized and redrawn
  });
}

const connectToRtmpSocket = (streamId) => {
  if (rtmpSocket.value) {
    rtmpSocket.value.disconnect()
  }
  
  rtmpSocket.value = io(`${SERVER_ROOT_URL}/rtmp`)
  
  rtmpSocket.value.on('connect', () => {
    console.log('已连接到RTMP WebSocket')
    rtmpSocket.value.emit('join_stream', { stream_id: streamId })
  })
  
  rtmpSocket.value.on('detection_result', (data) => {
    if (data.stream_id === currentRtmpStream.value) {
      alerts.value = data.alerts || []
      currentDetections.value = data.detections || [] // Update detections
      drawCanvas(); // Redraw canvas with new detections
    }
  })
  
  rtmpSocket.value.on('error', (error) => {
    console.error('RTMP WebSocket错误:', error)
  })

  rtmpSocket.value.on('disconnect', () => {
    console.log('RTMP WebSocket disconnected');
    currentDetections.value = []; // Clear detections on disconnect
    drawCanvas(); // Clear canvas
    startAlertPolling(); // Restart alert polling for general alerts if not connected to RTMP
  });
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
        currentDetections.value = []; // Clear detections
        if (rtmpSocket.value) {
          rtmpSocket.value.disconnect()
          rtmpSocket.value = null
        }
        drawCanvas(); // Clear canvas
      }
      await loadActiveStreams() // Refresh list immediately
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
          currentDetections.value = []; // Clear detections
          if (rtmpSocket.value) {
            rtmpSocket.value.disconnect()
            rtmpSocket.value = null
          }
          drawCanvas(); // Clear canvas
        }
        await loadActiveStreams() // Refresh list immediately
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

// New: Polling for RTMP stream list
const startRtmpListPolling = () => {
  if (rtmpListPollingIntervalId.value) {
    clearInterval(rtmpListPollingIntervalId.value);
  }
  rtmpListPollingIntervalId.value = setInterval(() => {
    loadActiveStreams();
  }, 5000); // Poll every 5 seconds
}

const stopRtmpListPolling = () => {
  if (rtmpListPollingIntervalId.value) {
    clearInterval(rtmpListPollingIntervalId.value);
    rtmpListPollingIntervalId.value = null;
  }
}

// Alert polling
let alertPollingInterval = null

const startAlertPolling = () => {
  if (alertPollingInterval) {
    clearInterval(alertPollingInterval)
  }
  
  alertPollingInterval = setInterval(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/alerts`)
      const data = await response.json()
      alerts.value = data.alerts || []
    } catch (error) {
      console.error('Error fetching alerts:', error)
      stopAlertPolling()
    }
  }, 2000)
}

const stopAlertPolling = () => {
  if (alertPollingInterval) {
    clearInterval(alertPollingInterval)
    alertPollingInterval = null
  }
}

// Sidebar control
const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}

// Helper methods
const isImageUrl = (url) => {
  const lowerUrl = url.toLowerCase()
  return lowerUrl.includes('.jpg') || lowerUrl.includes('.jpeg') || lowerUrl.includes('.png')
}

const isVideoUrl = (url) => {
  return url.toLowerCase().includes('.mp4') || url.toLowerCase().includes('.webm')
}

// Window resize responsiveness
const handleResize = () => {
  const newWidth = window.innerWidth
  windowWidth.value = newWidth
  
  if (newWidth >= 992 && !isSidebarOpen.value) {
    isSidebarOpen.value = true
  }
}

// Lifecycle hooks
onMounted(() => {
  loadConfig()
  loadRegisteredUsers()
  loadDetectionMode()
  startRtmpListPolling() // Start polling for RTMP streams list
  window.addEventListener('resize', handleResize);
})

onUnmounted(() => {
  if (pollingIntervalId.value) {
    clearInterval(pollingIntervalId.value)
  }
  
  // 停止所有正在运行的视频流
  disconnectWebcam(); // 这个函数现在会处理摄像头关闭
  closeRegistrationModal(true); // 组件卸载时确保清理, 并告知函数不要重启摄像头
  if (screamSocket) {
    screamSocket.disconnect();
    screamSocket = null;
  }

  disconnectWebcam();
  closeRegistrationModal(true);
  
  if (rtmpSocket.value) {
    rtmpSocket.value.disconnect()
  }
  stopAlertPolling();
  stopRtmpListPolling(); // Stop RTMP list polling
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
/* Global styles and resets */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: 'Inter', 'Segoe UI', Roboto, sans-serif;
}

.monitor-view-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

/* Page title styles */
.page-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  margin-bottom: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.title-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.title-icon {
  padding: 12px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  backdrop-filter: blur(10px);
}

.title-text h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.title-text p {
  margin: 4px 0 0;
  font-size: 14px;
  opacity: 0.8;
}

.title-actions {
  display: flex;
  gap: 16px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef4444;
  animation: pulse 2s infinite;
}

.status-indicator.active .status-dot {
  background: #22c55e;
}

.detection-mode-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 20px;
  backdrop-filter: blur(10px);
  font-size: 14px;
  font-weight: 500;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Face registration modal styles */
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
  color: #4CAF50;
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

/* RTMP modal styles */
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

/* Video container styles */
.video-container {
  position: relative;
  width: 100%;
  height: calc(100vh - 220px);
  padding: 24px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  margin: 0 24px 24px;
}

.video-container.sidebar-visible {
  width: calc(100% - 424px);
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.video-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: relative;
}

.video-content {
  flex: 1;
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  background: #000;
}

.video-frame {
  width: 100%;
  height: 100%;
  position: relative;
}

.webcam-feed,
.video-frame img,
.video-frame video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
}

.video-overlay {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.recording-indicator,
.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  color: white;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  backdrop-filter: blur(10px);
}

.recording-indicator {
  background: rgba(59, 130, 246, 0.9);
}

.file-info {
  background: rgba(34, 197, 94, 0.9);
}

.detection-info {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: rgba(16, 185, 129, 0.9);
  color: white;
  border-radius: 16px;
  font-size: 11px;
  font-weight: 500;
  backdrop-filter: blur(10px);
}

.recording-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: white;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* Loading state */
.loading-state {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #6b7280;
  gap: 20px;
}

.loading-content {
  text-align: center;
}

.loading-spinner {
  margin-bottom: 16px;
  color: #667eea;
}

.loading-progress {
  width: 200px;
  height: 4px;
  background: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
  margin-top: 16px;
}

.progress-bar {
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  animation: progress 2s ease-in-out infinite;
}

@keyframes progress {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

/* Placeholder state */
.video-placeholder {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
}

.placeholder-content {
  text-align: center;
  color: #64748b;
}

.placeholder-content h3 {
  margin: 16px 0 8px;
  font-size: 20px;
  font-weight: 600;
}

.placeholder-content p {
  font-size: 14px;
  opacity: 0.8;
  margin-bottom: 24px;
}

.quick-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}

.quick-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-weight: 500;
  font-size: 14px;
  width: 170px;
}

.quick-btn.primary {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
}

.quick-btn.secondary {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
}

.quick-btn.tertiary {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3);
}

.quick-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

/* Danger zone editing/detection Canvas */
.interaction-canvas {
  position: absolute;
  top: 0;
  left: 0;
  cursor: crosshair;
  z-index: 20;
}

/* Video fade animation */
.video-fade-enter-active,
.video-fade-leave-active {
  transition: all 0.5s ease;
}

.video-fade-enter-from,
.video-fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

/* Sidebar styles */
.control-sidebar {
  position: fixed;
  top: 60px;
  right: 0;
  height: calc(100vh - 60px);
  width: 400px;
  background: white;
  box-shadow: -4px 0 30px rgba(0, 0, 0, 0.1);
  transform: translateX(100%);
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 70;
  overflow: hidden;
  border-left: 1px solid #e5e7eb;
}

.control-sidebar.sidebar-open {
  transform: translateX(0);
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  border-bottom: 1px solid #e5e7eb;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-content h2 {
  margin: 0;
  color: #1f2937;
  font-size: 20px;
  font-weight: 600;
}

.close-btn {
  padding: 8px;
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  color: #6b7280;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: #f3f4f6;
  color: #374151;
}

.sidebar-content {
  height: calc(100% - 80px);
  overflow-y: auto;
  padding: 24px;
  scrollbar-width: thin;
  scrollbar-color: #d1d5db #f9fafb;
}

.sidebar-content::-webkit-scrollbar {
  width: 6px;
}

.sidebar-content::-webkit-scrollbar-track {
  background: #f9fafb;
}

.sidebar-content::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

/* Control panel sections */
.control-section {
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid #f3f4f6;
}

.control-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  position: relative;
}

.section-header h3 {
  margin: 0;
  color: #1f2937;
  font-size: 16px;
  font-weight: 600;
  flex: 1;
}

.alert-badge,
.user-count,
.stream-count {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 10px;
  min-width: 20px;
  text-align: center;
}

.user-count,
.stream-count {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
}

.mode-indicator {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 10px;
}

.edit-badge {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 10px;
}

/* Video controls */
.video-controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.control-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  background: white;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 500;
  font-size: 14px;
  width: 100%;
}

.control-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.control-btn.primary {
  border-color: #3b82f6;
  color: #3b82f6;
}

.control-btn.primary:hover,
.control-btn.primary.active {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
}

.control-btn.secondary {
  border-color: #10b981;
  color: #10b981;
}

.control-btn.secondary:hover {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
}

.control-btn.tertiary {
  border-color: #f59e0b;
  color: #f59e0b;
}

.control-btn.tertiary:hover {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3);
}

.control-btn.danger {
  border-color: #ef4444;
  color: #ef4444;
}

.control-btn.danger:hover {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
}

/* Detection modes grid */
.detection-modes-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.mode-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 12px;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  background: white;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 500;
  font-size: 12px;
}

.mode-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.mode-btn.active {
  border-color: #3b82f6;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
}

/* Danger zone controls */
.zone-controls {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.edit-instructions {
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
  border-left: 3px solid #3b82f6;
}

.instruction-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #6b7280;
}

.instruction-item:last-child {
  margin-bottom: 0;
}

/* Parameter settings */
.settings-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 16px;
}

.setting-item {
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
}

.setting-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.setting-header label {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.setting-value {
  font-size: 12px;
  font-weight: 600;
  color: #3b82f6;
  background: white;
  padding: 4px 8px;
  border-radius: 4px;
}

.setting-slider {
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background: #e5e7eb;
  outline: none;
  -webkit-appearance: none;
}

.setting-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
}

.setting-slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: none;
}

.apply-settings-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 500;
  font-size: 14px;
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
}

.apply-settings-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(16, 185, 129, 0.4);
}

/* User management */
.user-management {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
}

.add-user-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 500;
  font-size: 14px;
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
}

.add-user-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(16, 185, 129, 0.4);
}

.search-box {
  position: relative;
  width: 100%;
}

.search-input {
  width: 100%;
  padding: 12px 16px 12px 40px;
  border-radius: 10px;
  background: #f9fafb;
  color: #4b5563;
  font-size: 14px;
  outline: none;
  transition: all 0.3s ease;
  border: 1px solid #e5e7eb;
}

.search-input:focus {
  border-color: #60a5fa;
  box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.3);
}

.search-icon {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: #9ca3af;
}

.user-list-container {
  max-height: 220px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: #d1d5db #f9fafb;
}

.user-list-container::-webkit-scrollbar {
  width: 6px;
}

.user-list-container::-webkit-scrollbar-track {
  background: #f9fafb;
}

.user-list-container::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.user-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #ffffff;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  border: 1px solid #e5e7eb;
}

.user-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
}

.user-details {
  display: flex;
  flex-direction: column;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.user-status {
  font-size: 12px;
  color: #6b7280;
}

.user-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #f3f4f6;
  color: #6b7280;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
}

.action-btn:hover {
  background: #e5e7eb;
}

.action-btn.delete:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

/* RTMP stream management */
.stream-list {
  max-height: 300px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: #d1d5db #f9fafb;
}

.stream-list::-webkit-scrollbar {
  width: 6px;
}

.stream-list::-webkit-scrollbar-track {
  background: #f9fafb;
}

.stream-list::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.stream-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #ffffff;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  border: 1px solid #e5e7eb;
  margin-bottom: 12px;
}

.stream-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.stream-info {
  flex: 1;
}

.stream-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.stream-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.stream-status {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
}

.stream-status.active {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
}

.stream-status.inactive {
  background: rgba(107, 114, 128, 0.1);
  color: #6b7280;
}

.stream-status.error {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.stream-url {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
  word-break: break-all;
}

.stream-controls {
  display: flex;
  gap: 8px;
}

.stream-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stream-btn.select {
  background: #e0f2fe;
  color: #0284c7;
}

.stream-btn.select:hover {
  background: #0284c7;
  color: white;
}

.stream-btn.select.active {
  background: #0284c7;
  color: white;
}

.stream-btn.stop {
  background: #fef3c7;
  color: #d97706;
}

.stream-btn.stop:hover {
  background: #d97706;
  color: white;
}

.stream-btn.delete {
  background: #fee2e2;
  color: #dc2626;
}

.stream-btn.delete:hover {
  background: #dc2626;
  color: white;
}

/* Alert information */
.alerts-container {
  max-height: 240px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: #d1d5db #f9fafb;
}

.alerts-container::-webkit-scrollbar {
  width: 6px;
}

.alerts-container::-webkit-scrollbar-track {
  background: #f9fafb;
}

.alerts-container::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.alert-item {
  padding: 12px 16px;
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  transition: all 0.3s ease;
  border-left: 4px solid #ef4444;
}

.alert-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.alert-time {
  font-size: 12px;
  color: #6b7280;
}

.alert-message {
  font-size: 14px;
  color: #1f2937;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 0;
  text-align: center;
  color: #9ca3af;
}

.empty-state p {
  margin-top: 12px;
  font-size: 14px;
}

/* Floating control button */
.floating-control {
  position: fixed;
  z-index: 60;
  cursor: grab;
  transition: all 0.3s ease;
}

.sidebar-toggle-btn {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
  border: none;
}

.sidebar-toggle-btn:hover {
  transform: scale(1.05);
  box-shadow: 0 10px 30px rgba(102, 126, 234, 0.5);
}

.sidebar-toggle-btn.sidebar-open {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
}

/* Icon rotation animation */
.icon-rotate-enter-active,
.icon-rotate-leave-active {
  transition: transform 0.3s ease;
}

.icon-rotate-enter-from,
.icon-rotate-leave-to {
  transform: rotate(180deg);
}

/* List animations */
.user-list-enter-active,
.user-list-leave-active,
.alert-list-enter-active,
.alert-list-leave-active {
  transition: all 0.3s ease;
}

.user-list-enter-from,
.user-list-leave-to,
.alert-list-enter-from,
.alert-list-leave-to {
  opacity: 0;
  transform: translateX(30px);
}

/* Responsive layout */
@media (max-width: 1200px) {
  .video-container {
    width: calc(100% - 360px);
  }
  
  .control-sidebar {
    width: 340px;
  }
}

@media (max-width: 992px) {
  .video-container {
    width: 100%;
    margin: 0 0 24px;
    border-radius: 0;
  }
  
  .control-sidebar {
    transform: translateX(100%);
    width: 380px;
  }
  
  .control-sidebar.sidebar-open {
    transform: translateX(0);
  }
  
  .floating-control {
    display: block;
  }
}

@media (max-width: 768px) {
  .page-title {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    padding: 20px 24px;
  }
  
  .title-content {
    gap: 12px;
  }
  
  .title-icon {
    padding: 8px;
  }
  
  .title-text h1 {
    font-size: 24px;
  }
  
  .title-text p {
    font-size: 13px;
  }
  
  .title-actions {
    width: 100%;
    justify-content: space-between;
  }
  
  .status-indicator,
  .detection-mode-badge {
    padding: 6px 12px;
    font-size: 13px;
  }
  
  .video-container {
    height: calc(100vh - 240px);
    padding: 16px;
  }
  
  .quick-actions {
    flex-direction: column;
  }
  
  .control-sidebar {
    width: 100%;
    z-index: 100;
  }
  
  .detection-modes-grid {
    grid-template-columns: 1fr;
  }
  
  .zone-controls {
    flex-direction: column;
  }
}

@media (max-width: 480px) {
  .registration-modal-content,
  .rtmp-modal-content {
    width: 95%;
    padding: 20px;
  }
  
  .registration-controls,
  .rtmp-controls {
    flex-direction: column;
    gap: 12px;
  }
  
  .registration-controls button,
  .rtmp-controls button {
    width: 100%;
  }
}
scream-status-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: #222;
  color: #fff;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 1.1em;
}
.scream-status-bar button {
  background: #007bff;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 0.3rem 1rem;
  cursor: pointer;
}
.scream-status-bar button:hover {
  background: #0056b3;
}
.scream-volume-bar {
  width: 120px;
  height: 18px;
  background: #444;
  border-radius: 8px;
  overflow: hidden;
  margin-left: 1.5rem;
  display: flex;
  align-items: center;
}
.scream-volume-inner {
  height: 100%;
  transition: width 0.1s, background 0.2s;
}
</style>