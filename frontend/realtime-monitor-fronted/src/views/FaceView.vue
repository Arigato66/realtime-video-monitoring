<template>
  <div class="face-view-page">
    <!-- 引入顶部栏组件 -->
    <TopBar />
            
    <!-- 页面标题区域 -->
    <div class="page-title">
      <div class="title-content">
        <div class="title-icon">
          <Camera class="w-8 h-8" />
        </div>
        <div class="title-text">
          <h1>入站人脸识别</h1>
          <p>实时 · 高精度</p>
        </div>
      </div>
      <div class="title-actions">
        <div class="status-indicator" :class="statusIndicatorClass">
          <div class="status-dot"></div>
          <span>{{ statusText }}</span>
        </div>
        <div class="face-count-badge">
          <Users class="w-4 h-4" />
          <span>{{ registeredUsers.length }} 人员</span>
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

    <!-- 视频区域 -->
    <div class="video-container" :class="{ 'sidebar-visible': isSidebarOpen }">
      <div class="video-wrapper">
        <div class="video-content">
          <transition name="video-fade" mode="out-in">
            <!-- 摄像头实时画面 -->
            <div v-if="activeSource === 'webcam'" key="webcam" class="video-frame">
              <img ref="webcamImg" :src="videoSource" alt="摄像头实时画面" class="webcam-feed" />
              <div class="video-overlay">
                <div class="recording-indicator">
                  <div class="recording-dot"></div>
                  <span>人脸识别中</span>
                </div>
                <div class="detection-info">
                  <Eye class="w-4 h-4" />
                  <span>人脸检测模式</span>
                </div>
                <!-- 实时识别结果显示 -->
                <div v-if="lastRecognitionResult" class="recognition-result">
                  <div class="result-badge" :class="lastRecognitionResult.type">
                    <User class="w-4 h-4" />
                    <span>{{ lastRecognitionResult.name }}</span>
                  </div>
                  <div class="confidence-bar">
                    <div class="confidence-fill" :style="{ width: `${lastRecognitionResult.confidence}%` }"></div>
                  </div>
                </div>
              </div>
            </div>
            <!-- 上传文件 -->
            <div v-else-if="activeSource === 'upload'" key="upload" class="video-frame">
              <img v-if="isImageUrl(videoSource)" :src="videoSource" alt="上传的图像" />
              <video v-else-if="isVideoUrl(videoSource)" :src="videoSource" controls autoplay></video>
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
                <Camera class="w-16 h-16 text-gray-400" />
                <h3>开始人脸识别</h3>
                <p>请开启摄像头或上传文件进行人脸识别</p>
                <div class="quick-actions">
                  <button @click="connectWebcam" class="quick-btn primary">
                    <Video class="w-4 h-4" />
                    <span>开启摄像头</span>
                  </button>
                  <button @click="uploadVideoFile" class="quick-btn secondary">
                    <Upload class="w-4 h-4" />
                    <span>上传文件</span>
                  </button>
                </div>
              </div>
            </div>
          </transition>
        </div>
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
              @click="uploadVideoFile"
              :disabled="activeSource === 'webcam'"
              class="control-btn secondary"
            >
              <Upload class="w-4 h-4" />
              <span>上传文件</span>
            </button>
          </div>
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
                :key="user.name"
                class="user-item"
              >
                <div class="user-info">
                  <div class="user-avatar">
                    <User class="w-4 h-4" />
                  </div>
                  <div class="user-details">
                    <span class="user-name">{{ user.name }}</span>
                    <span class="user-status">
                      已注册 · 今日识别 {{ user.todayCount || 0 }} 次
                    </span>
                    <span class="last-seen" v-if="user.lastSeen">
                      最后识别: {{ formatRelativeTime(user.lastSeen) }}
                    </span>
                  </div>
                </div>
                <div class="user-actions">
                  <button @click="viewUserDetails(user)" class="action-btn view">
                    <Eye class="w-3 h-3" />
                  </button>
                  <button @click="deleteFace(user.name)" class="action-btn delete">
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

        <!-- 识别统计 -->
        <div class="control-section">
          <div class="section-header">
            <BarChart3 class="w-4 h-4" />
            <h3>识别统计</h3>
            <div class="stats-refresh" @click="refreshStats">
              <RefreshCw class="w-3 h-3" :class="{ 'animate-spin': isRefreshingStats }" />
            </div>
          </div>
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon">
                <Users class="w-5 h-5" />
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ recognitionStats.registeredUsers }}</div>
                <div class="stat-label">注册人员</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon success">
                <CheckCircle class="w-5 h-5" />
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ recognitionStats.successfulRecognitions }}</div>
                <div class="stat-label">识别成功</div>
                <div class="stat-change" :class="{ positive: recognitionStats.successChange > 0 }">
                  {{ recognitionStats.successChange > 0 ? '+' : '' }}{{ recognitionStats.successChange }}
                </div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon warning">
                <AlertCircle class="w-5 h-5" />
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ recognitionStats.unknownFaces }}</div>
                <div class="stat-label">未知人员</div>
                <div class="stat-change" :class="{ negative: recognitionStats.unknownChange > 0 }">
                  {{ recognitionStats.unknownChange > 0 ? '+' : '' }}{{ recognitionStats.unknownChange }}
                </div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon info">
                <Clock class="w-5 h-5" />
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ recognitionStats.todayTotal }}</div>
                <div class="stat-label">今日识别</div>
                <div class="stat-sublabel">去重后: {{ recognitionStats.todayUnique }}</div>
              </div>
            </div>
          </div>
          
          <!-- 实时识别率图表 -->
          <div class="recognition-rate-chart">
            <div class="chart-header">
              <h4>实时识别率</h4>
              <span class="current-rate">{{ recognitionStats.currentRate }}%</span>
            </div>
            <div class="rate-bars">
              <div 
                v-for="(rate, index) in recognitionRateHistory" 
                :key="index"
                class="rate-bar"
                :style="{ height: `${rate}%` }"
              ></div>
            </div>
          </div>
        </div>

        <!-- 告警信息 -->
        <div class="control-section">
          <div class="section-header">
            <AlertTriangle class="w-4 h-4" />
            <h3>告警信息</h3>
            <div v-if="newAlertCount > 0" class="alert-badge">
              {{ newAlertCount }}
            </div>
          </div>
          <div class="alerts-container" :class="{ 'has-alerts': alerts.length > 0 }">
            <transition-group name="alert-list" tag="div" class="alert-list">
              <div
                v-for="(alert, index) in alerts"
                :key="`alert-${index}-${alert.timestamp}`"
                class="alert-item"
                :class="{ 'alert-new': alert.isNew }"
                @click="markAsRead(alert, index)"
              >
                <div class="alert-header">
                  <AlertCircle class="w-3 h-3" />
                  <span class="alert-time">{{ formatTime(alert.timestamp) }}</span>
                </div>
                <p class="alert-message">{{ alert.message }}</p>
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
      @mousedown="startDrag"
      @touchstart="startDrag"
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

    <!-- 告警通知 -->
    <transition name="notification">
      <div v-if="showNotification" class="alert-notification">
        <div class="notification-content">
          <AlertTriangle class="w-5 h-5 text-orange-500" />
          <div class="notification-text">
            <p class="notification-title">新告警</p>
            <p class="notification-message">{{ latestAlert }}</p>
          </div>
        </div>
        <button @click="hideNotification" class="notification-close">
          <X class="w-4 h-4" />
        </button>
      </div>
    </transition>

    <!-- 用户详情模态框 -->
    <div v-if="showUserDetailsModal" class="user-details-modal-overlay">
      <div class="user-details-modal-content">
        <div class="modal-header">
          <h2>{{ selectedUser?.name }} - 详细信息</h2>
          <button @click="closeUserDetailsModal" class="close-btn">
            <X class="w-5 h-5" />
          </button>
        </div>
        <div class="modal-body">
          <div class="user-stats-grid">
            <div class="user-stat-item">
              <div class="stat-label">总识别次数</div>
              <div class="stat-value">{{ selectedUser?.totalRecognitions || 0 }}</div>
            </div>
            <div class="user-stat-item">
              <div class="stat-label">今日识别次数</div>
              <div class="stat-value">{{ selectedUser?.todayCount || 0 }}</div>
            </div>
            <div class="user-stat-item">
              <div class="stat-label">首次注册时间</div>
              <div class="stat-value">{{ formatDate(selectedUser?.registeredAt) }}</div>
            </div>
            <div class="user-stat-item">
              <div class="stat-label">最后识别时间</div>
              <div class="stat-value">{{ formatDate(selectedUser?.lastSeen) }}</div>
            </div>
          </div>
          <div class="recognition-history">
            <h3>最近识别记录</h3>
            <div class="history-list">
              <div 
                v-for="record in selectedUser?.recentRecognitions || []" 
                :key="record.id"
                class="history-item"
              >
                <div class="history-time">{{ formatTime(record.timestamp) }}</div>
                <div class="history-confidence">置信度: {{ record.confidence }}%</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { ref, onMounted, onUnmounted, computed, reactive, nextTick } from 'vue'
import io from 'socket.io-client'
import TopBar from '../components/TopBar.vue'

// 导入图标
import {
  Camera, Video, Upload, Square, Settings, ChevronLeft, X, PlayCircle,
  AlertTriangle, AlertCircle, Shield, Users, UserPlus, User, UserX, Trash2,
  FileImage, Loader2, Eye, Search, BarChart3, CheckCircle, Clock, Cog, Check,
  RefreshCw
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


// 删除这些重复的声明（第119-122行）：
// const SERVER_ROOT_URL = 'http://localhost:5000'
// const API_BASE_URL = `${SERVER_ROOT_URL}/api`
// const VIDEO_FEED_URL = `${API_BASE_URL}/video_feed`

// API端点设置（修改后）
const SERVER_ROOT_URL = '' // 使用相对路径
const API_BASE_URL = '/api'

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
const alerts = ref([])
const registeredUsers = ref([])
const pollingIntervalId = ref(null)
const videoTaskId = ref('')
const newAlertCount = ref(0)
const searchQuery = ref('')
const webcamImg = ref(null)

// 通知相关
const showNotification = ref(false)
const latestAlert = ref('')

// 用户详情模态框
const showUserDetailsModal = ref(false)
const selectedUser = ref(null)

// 实时识别结果
const lastRecognitionResult = ref(null)

// 统计数据刷新状态
const isRefreshingStats = ref(false)

// 识别统计 - 增强版
const recognitionStats = ref({
  registeredUsers: 0,
  successfulRecognitions: 0,
  unknownFaces: 0,
  todayTotal: 0,
  todayUnique: 0,
  currentRate: 0,
  successChange: 0,
  unknownChange: 0
})

// 识别率历史数据
const recognitionRateHistory = ref(Array(20).fill(0))

// 识别记录去重管理
const recognitionCache = reactive({
  dailyRecognitions: new Map(), // 每日识别记录
  recentRecognitions: [], // 最近识别记录
  duplicateThreshold: 30000 // 30秒内的重复识别将被过滤
})

// 定时器管理
const timers = reactive({
  statsUpdate: null,
  alertPolling: null,
  recognitionRateUpdate: null,
  cacheCleanup: null
})

// 停止媒体流的辅助函数
const stopStream = (stream) => {
  if (stream && stream.getTracks) {
    stream.getTracks().forEach(track => track.stop())
  }
}

// 计算属性
const statusIndicatorClass = computed(() => ({
  active: activeSource.value === 'webcam'
}))

const statusText = computed(() => {
  return activeSource.value === 'webcam' ? '人脸识别中' : '识别已停止'
})

const floatingButtonStyle = computed(() => ({
  left: `${floatingButton.x}px`,
  top: `${floatingButton.y}px`,
  cursor: floatingButton.isDragging ? 'grabbing' : 'grab'
}))

const filteredUsers = computed(() => {
  if (!searchQuery.value) return registeredUsers.value
  return registeredUsers.value.filter(user =>
    user.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

// 时间格式化函数
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

const formatDate = (timestamp) => {
  if (!timestamp) return '未知'
  const date = new Date(timestamp)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

const formatRelativeTime = (timestamp) => {
  if (!timestamp) return ''
  const now = new Date()
  const time = new Date(timestamp)
  const diff = now - time
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return `${Math.floor(diff / 86400000)}天前`
}

// 识别记录去重处理
const processRecognitionResult = (result) => {
  const now = Date.now()
  const userId = result.name || 'unknown'
  const today = new Date().toDateString()
  
  // 检查是否为重复识别
  const recentSame = recognitionCache.recentRecognitions.find(r => 
    r.userId === userId && 
    (now - r.timestamp) < recognitionCache.duplicateThreshold
  )
  
  if (recentSame) {
    console.log(`过滤重复识别: ${userId}`)
    return false
  }
  
  // 添加到最近识别记录
  recognitionCache.recentRecognitions.push({
    userId,
    timestamp: now,
    confidence: result.confidence || 0
  })
  
  // 清理过期记录
  recognitionCache.recentRecognitions = recognitionCache.recentRecognitions.filter(
    r => (now - r.timestamp) < recognitionCache.duplicateThreshold * 2
  )
  
  // 更新每日统计
  if (!recognitionCache.dailyRecognitions.has(today)) {
    recognitionCache.dailyRecognitions.set(today, new Set())
  }
  
  const todaySet = recognitionCache.dailyRecognitions.get(today)
  const wasNewToday = !todaySet.has(userId)
  todaySet.add(userId)
  
  // 更新用户数据
  const userIndex = registeredUsers.value.findIndex(u => u.name === userId)
  if (userIndex !== -1) {
    registeredUsers.value[userIndex].lastSeen = now
    registeredUsers.value[userIndex].todayCount = (registeredUsers.value[userIndex].todayCount || 0) + 1
    registeredUsers.value[userIndex].totalRecognitions = (registeredUsers.value[userIndex].totalRecognitions || 0) + 1
    
    // 添加到最近识别记录
    if (!registeredUsers.value[userIndex].recentRecognitions) {
      registeredUsers.value[userIndex].recentRecognitions = []
    }
    registeredUsers.value[userIndex].recentRecognitions.unshift({
      id: now,
      timestamp: now,
      confidence: result.confidence || 0
    })
    
    // 只保留最近10条记录
    registeredUsers.value[userIndex].recentRecognitions = 
      registeredUsers.value[userIndex].recentRecognitions.slice(0, 10)
  }
  
  return true
}

// 标记告警为已读
const markAsRead = (alert, index) => {
  if (alert.isNew) {
    alerts.value[index].isNew = false
    newAlertCount.value--
  }
}

// API调用封装
const apiFetch = async (endpoint, options = {}) => {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, options)
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: response.statusText }))
      throw new Error(errorData.message || `服务器错误: ${response.status}`)
    }
    return await response.json()
  } catch (error) {
    console.error(`API调用失败 ${endpoint}:`, error)
    alert(`操作失败: ${error.message}`)
    throw error
  }
}

// Dlib API调用封装
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

// 人脸管理方法
const loadRegisteredUsers = async () => {
  try {
    const data = await dlibApiFetch('/faces')
    const users = (data.names || []).map(name => ({
      name,
      registeredAt: Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000, // 模拟注册时间
      lastSeen: null,
      todayCount: 0,
      totalRecognitions: 0,
      recentRecognitions: []
    }))
    registeredUsers.value = users
    recognitionStats.value.registeredUsers = users.length
  } catch (error) {
    console.error('加载注册用户失败:', error)
  }
}

const deleteFace = async (name) => {
  if (confirm(`确定要删除人员 '${name}' 吗?`)) {
    try {
      const data = await dlibApiFetch(`/faces/${name}`, { method: 'DELETE' })
      alert(data.message)
      loadRegisteredUsers()
    } catch (error) {
      console.error('删除用户失败:', error)
    }
  }
}

// 查看用户详情
const viewUserDetails = (user) => {
  selectedUser.value = user
  showUserDetailsModal.value = true
}

const closeUserDetailsModal = () => {
  showUserDetailsModal.value = false
  selectedUser.value = null
}

// 人脸注册功能
const registerFace = () => {
  const name = prompt("请输入要注册人员的姓名:")
  if (name && name.trim()) {
    // 检查主摄像头是否正在运行，如果是，则先停止它
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
        
    // 使用 nextTick 并增加一个短暂延时，以确保摄像头已被释放
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

  // 1. 获取本地摄像头权限
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

  // 2. 连接到 WebSocket
  registrationSocket.value = io(`${SERVER_ROOT_URL}/dlib/register`)
    
  registrationSocket.value.on('connect', () => {
    console.log('已连接到注册 WebSocket')
    registrationStatus.value = '连接成功，正在开始...'
    // 发送开始指令
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
    
  // 将帧数据转为 base64
  const imageData = canvas.toDataURL('image/jpeg')
    
  // 通过 WebSocket 发送
  registrationSocket.value.emit('frame_for_capture', { image: imageData })
  registrationStatus.value = '已发送捕获请求...'
}

// 在关闭模态框时停止视频流
const closeRegistrationModal = (isUnmounting = false) => {
  showRegistrationModal.value = false
  registrationName.value = ''
  registrationStatus.value = ''
  capturedFramesCount.value = 0
    
  // 停止摄像头
  if (localStream.value && localStream.value.getTracks) {
    localStream.value.getTracks().forEach(track => track.stop())
    localStream.value = null
  }
    
  // 断开 socket 连接
  if (registrationSocket.value) {
    registrationSocket.value.disconnect()
    registrationSocket.value = null
  }
    
  // 如果不是在组件卸载时调用，并且之前摄像头是开启的，则重新连接
  if (!isUnmounting && wasWebcamActive.value) {
    connectWebcam()
    wasWebcamActive.value = false
  }
    
  // 刷新用户列表
  loadRegisteredUsers()
}

// 视频控制方法
const connectWebcam = () => {
  stopPolling()
  activeSource.value = 'webcam'
  nextTick(() => {
    if (webcamImg.value) {
      webcamImg.value.src = `${VIDEO_FEED_URL}?t=${new Date().getTime()}`
    }
  })
  videoSource.value = `${VIDEO_FEED_URL}?t=${new Date().getTime()}`
  startAlertPolling()
  startRealTimeRecognition()
  forceFaceOnlyMode()
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
    if (webcamImg.value) webcamImg.value.src = ''
    videoSource.value = ''
    stopAlertPolling()
    stopRealTimeRecognition()
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
            
      alerts.value = (data.alerts || []).map(alert => ({
        message: alert,
        timestamp: new Date(),
        isNew: true
      }))
      newAlertCount.value = alerts.value.length
      stopAlertPolling()
    } else {
      const errorData = await response.json()
      throw new Error(errorData.message || '文件上传失败')
    }
  } catch (error) {
    activeSource.value = ''
    alert(error.message || '操作失败')
  }
}

// 轮询相关方法
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
      alerts.value = (data.alerts || []).map(alert => ({
        message: alert,
        timestamp: new Date(),
        isNew: true
      }))
      newAlertCount.value = alerts.value.length
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
    alert(error.message)
  }
}

// 实时识别功能
const startRealTimeRecognition = () => {
  // 模拟实时识别结果
  timers.recognitionRateUpdate = setInterval(() => {
    // 模拟识别结果
    if (Math.random() > 0.7) {
      const isKnown = Math.random() > 0.3
      const result = {
        name: isKnown ? registeredUsers.value[Math.floor(Math.random() * registeredUsers.value.length)]?.name || '未知人员' : '未知人员',
        confidence: Math.floor(Math.random() * 30) + 70,
        type: isKnown ? 'known' : 'unknown'
      }
      
      lastRecognitionResult.value = result
      
      // 处理识别结果
      if (processRecognitionResult(result)) {
        updateStatsFromRecognition(result)
      }
      
      // 3秒后清除显示
      setTimeout(() => {
        lastRecognitionResult.value = null
      }, 3000)
    }
    
    // 更新识别率历史
    const newRate = Math.floor(Math.random() * 40) + 60
    recognitionRateHistory.value.shift()
    recognitionRateHistory.value.push(newRate)
    recognitionStats.value.currentRate = newRate
  }, 2000)
}

const stopRealTimeRecognition = () => {
  if (timers.recognitionRateUpdate) {
    clearInterval(timers.recognitionRateUpdate)
    timers.recognitionRateUpdate = null
  }
  lastRecognitionResult.value = null
}

// 从识别结果更新统计数据
const updateStatsFromRecognition = (result) => {
  const prevStats = { ...recognitionStats.value }
  
  if (result.type === 'known') {
    recognitionStats.value.successfulRecognitions++
  } else {
    recognitionStats.value.unknownFaces++
  }
  
  recognitionStats.value.todayTotal++
  
  // 计算今日去重数量
  const today = new Date().toDateString()
  const todaySet = recognitionCache.dailyRecognitions.get(today) || new Set()
  recognitionStats.value.todayUnique = todaySet.size
  
  // 计算变化量
  recognitionStats.value.successChange = recognitionStats.value.successfulRecognitions - prevStats.successfulRecognitions
  recognitionStats.value.unknownChange = recognitionStats.value.unknownFaces - prevStats.unknownFaces
}

// 告警轮询
const startAlertPolling = () => {
  if (timers.alertPolling) clearInterval(timers.alertPolling)
    
  timers.alertPolling = setInterval(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/alerts`)
      const data = await response.json()
            
      if (data.alerts && data.alerts.length) {
        const newAlerts = data.alerts
          .filter(alert => !alerts.value.some(a => a.message === alert))
          .map(alert => ({
            message: alert,
            timestamp: new Date(),
            isNew: true
          }))
                
        if (newAlerts.length) {
          alerts.value = [...alerts.value, ...newAlerts]
          newAlertCount.value += newAlerts.length
                    
          // 显示通知
          if (windowWidth.value < 768 && !isSidebarOpen.value) {
            showAlertNotification(newAlerts[0].message)
          }
        }
      }
    } catch (error) {
      console.error('获取告警失败:', error)
      stopAlertPolling()
    }
  }, 2000)
}

const stopAlertPolling = () => {
  if (timers.alertPolling) {
    clearInterval(timers.alertPolling)
    timers.alertPolling = null
  }
}

// 统计数据更新
const updateStats = async () => {
  try {
    // 这里应该调用真实的API获取统计数据
    // const response = await apiFetch('/stats')
    // const data = response.data
    
    // 模拟API调用
    const prevStats = { ...recognitionStats.value }
    
    // 模拟统计数据更新
    recognitionStats.value = {
      ...recognitionStats.value,
      registeredUsers: registeredUsers.value.length,
      // 其他统计数据保持当前值或从API获取
    }
    
    console.log('统计数据已更新')
  } catch (error) {
    console.error('更新统计数据失败:', error)
  }
}

const refreshStats = async () => {
  isRefreshingStats.value = true
  try {
    await updateStats()
    await loadRegisteredUsers()
  } finally {
    setTimeout(() => {
      isRefreshingStats.value = false
    }, 1000)
  }
}

// 启动定期统计更新
const startStatsUpdate = () => {
  timers.statsUpdate = setInterval(updateStats, 30000) // 每30秒更新一次
}

const stopStatsUpdate = () => {
  if (timers.statsUpdate) {
    clearInterval(timers.statsUpdate)
    timers.statsUpdate = null
  }
}

// 缓存清理
const startCacheCleanup = () => {
  timers.cacheCleanup = setInterval(() => {
    const now = Date.now()
    const yesterday = new Date(now - 24 * 60 * 60 * 1000).toDateString()
    
    // 清理过期的每日识别记录
    for (const [date, records] of recognitionCache.dailyRecognitions.entries()) {
      if (date < yesterday) {
        recognitionCache.dailyRecognitions.delete(date)
      }
    }
    
    // 清理过期的最近识别记录
    recognitionCache.recentRecognitions = recognitionCache.recentRecognitions.filter(
      r => (now - r.timestamp) < recognitionCache.duplicateThreshold * 2
    )
  }, 60000) // 每分钟清理一次
}

// 通知相关方法
const showAlertNotification = (message) => {
  latestAlert.value = message
  showNotification.value = true
    
  setTimeout(() => {
    hideNotification()
  }, 5000)
}

const hideNotification = () => {
  showNotification.value = false
}

// 模式设置
const forceFaceOnlyMode = async () => {
  try {
    await apiFetch('/detection_mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'face_only' })
    })
  } catch (error) {
    console.error('设置人脸识别模式失败:', error)
  }
}

// 侧边栏控制
const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}

// 悬浮按钮拖动控制
const startDrag = (e) => {
  e.preventDefault()
    
  const touchEvent = e.touches?.[0] || e
  const rect = e.currentTarget.getBoundingClientRect()
    
  floatingButton.isDragging = true
  floatingButton.offsetX = touchEvent.clientX - rect.left
  floatingButton.offsetY = touchEvent.clientY - rect.top
    
  document.addEventListener('mousemove', handleDrag)
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchmove', handleDrag, { passive: false })
  document.addEventListener('touchend', stopDrag)
}

const handleDrag = (e) => {
  if (!floatingButton.isDragging) return
    
  const touchEvent = e.touches?.[0] || e
    
  // 计算新位置，确保按钮不会移出可视区域
  let newX = touchEvent.clientX - floatingButton.offsetX
  let newY = touchEvent.clientY - floatingButton.offsetY
    
  // 边界检查
  const buttonWidth = 48
  const buttonHeight = 48
  const maxX = window.innerWidth - buttonWidth
  const maxY = window.innerHeight - buttonHeight
    
  newX = Math.max(0, Math.min(newX, maxX))
  newY = Math.max(0, Math.min(newY, maxY))
    
  floatingButton.x = newX
  floatingButton.y = newY
}

const stopDrag = () => {
  floatingButton.isDragging = false
  document.removeEventListener('mousemove', handleDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', handleDrag)
  document.removeEventListener('touchend', stopDrag)
}

// 窗口大小响应
const handleResize = () => {
  const newWidth = window.innerWidth
  windowWidth.value = newWidth
    
  if (newWidth >= 992 && !isSidebarOpen.value) {
    isSidebarOpen.value = true
  }
}

// 生命周期
onMounted(() => {
  window.addEventListener('resize', handleResize)
  handleResize()
    
  loadRegisteredUsers()
  forceFaceOnlyMode()
  updateStats()
  startStatsUpdate()
  startCacheCleanup()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  
  // 清理所有定时器
  Object.values(timers).forEach(timer => {
    if (timer) clearInterval(timer)
  })
  
  stopPolling()
  closeRegistrationModal(true)
  stopRealTimeRecognition()
  
  document.removeEventListener('mousemove', handleDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', handleDrag)
  document.removeEventListener('touchend', stopDrag)
})

// 辅助方法
const isImageUrl = (url) => {
  const lowerUrl = url.toLowerCase()
  return lowerUrl.includes('.jpg') || lowerUrl.includes('.jpeg') || lowerUrl.includes('.png')
}

const isVideoUrl = (url) => {
  return url.toLowerCase().includes('.mp4') || url.toLowerCase().includes('.webm')
}
</script>

<style scoped>
/* 全局样式重置与基础设置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: 'Inter', 'Segoe UI', Roboto, sans-serif;
}

.face-view-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

/* 页面标题样式 */
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

.face-count-badge {
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

/* 人脸注册模态框样式 */
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

/* 视频容器样式 */
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

/* 实时识别结果显示 */
.recognition-result {
  background: rgba(0, 0, 0, 0.8);
  border-radius: 12px;
  padding: 12px;
  backdrop-filter: blur(10px);
  min-width: 200px;
}

.result-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
}

.result-badge.known {
  background: rgba(34, 197, 94, 0.9);
  color: white;
}

.result-badge.unknown {
  background: rgba(239, 68, 68, 0.9);
  color: white;
}

.confidence-bar {
  width: 100%;
  height: 4px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 2px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  background: linear-gradient(90deg, #22c55e, #16a34a);
  transition: width 0.3s ease;
}

/* 加载状态 */
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

/* 占位符状态 */
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
}

.quick-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-weight: 500;
  font-size: 14px;
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

.quick-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

/* 视频淡入淡出动画 */
.video-fade-enter-active,
.video-fade-leave-active {
  transition: all 0.5s ease;
}

.video-fade-enter-from,
.video-fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

/* 侧边栏样式 */
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

/* 控制面板区域 */
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
.user-count {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 10px;
  min-width: 20px;
  text-align: center;
}

.user-count {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
}

/* 视频控制 */
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

.control-btn.danger {
  border-color: #ef4444;
  color: #ef4444;
}

.control-btn.danger:hover {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
}

/* 人员管理 */
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
  border: 2px;
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
  border: 1px;
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

.action-btn.view:hover {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
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

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.stat-card {
  padding: 16px;
  background: #f9fafb;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.stat-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(59, 130, 246, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3b82f6;
  margin-bottom: 12px;
}

.stat-icon.success {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
}

.stat-icon.warning {
  background: rgba(249, 115, 22, 0.1);
  color: #f97316;
}

.stat-icon.info {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: #6b7280;
}

/* 告警信息 */
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
  cursor: pointer;
}

.alert-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.alert-item.alert-new {
  border-left: 4px solid #ef4444;
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

/* 悬浮控制按钮 */
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

/* 图标旋转动画 */
.icon-rotate-enter-active,
.icon-rotate-leave-active {
  transition: transform 0.3s ease;
}

.icon-rotate-enter-from,
.icon-rotate-leave-to {
  transform: rotate(180deg);
}

/* 告警通知 */
.alert-notification {
  position: fixed;
  top: 80px;
  right: 24px;
  padding: 16px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
  z-index: 80;
  display: flex;
  align-items: center;
  gap: 16px;
  max-width: 360px;
  transform: translateX(calc(100% + 40px));
  transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  border-left: 4px solid #f97316;
}

.alert-notification.active {
  transform: translateX(0);
}

.notification-content {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.notification-text {
  display: flex;
  flex-direction: column;
}

.notification-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.notification-message {
  font-size: 13px;
  color: #4b5563;
}

.notification-close {
  padding: 4px;
  background: transparent;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.2s ease;
}

.notification-close:hover {
  color: #4b5563;
}

/* 通知动画 */
.notification-enter-active {
  transition: all 0.5s ease;
}

.notification-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}

/* 响应式布局 */
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
  .face-count-badge {
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
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .alert-notification {
    top: auto;
    bottom: 24px;
    left: 24px;
    right: 24px;
    max-width: none;
  }
}

@media (max-width: 480px) {
  .registration-modal-content {
    width: 95%;
    padding: 20px;
  }
  
  .registration-controls {
    flex-direction: column;
    gap: 12px;
  }
  
  .registration-controls button {
    width: 100%;
  }
}
</style>
