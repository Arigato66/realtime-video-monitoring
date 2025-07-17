<template>
  <div class="alert-view-page">
    <!-- 引入顶部栏组件 -->
    <TopBar />
            
    <!-- 页面标题区域 -->
    <div class="page-title">
      <div class="title-content">
        <div class="title-icon">
          <AlertTriangle class="w-8 h-8" />
        </div>
        <div class="title-text">
          <h1>告警中心</h1>
          <p>查看和管理所有监控告警</p>
        </div>
      </div>
      <div class="title-actions">
        <button @click="goToSystemLogs" class="system-logs-button">
          <List class="w-4 h-4" />
          <span>查看系统日志</span>
        </button>
      </div>
    </div>

    <!-- 告警统计信息 -->
    <div class="stats-container">
      <div class="stat-card unprocessed">
        <div class="stat-header">
          <Clock class="w-6 h-6" />
          <h3>未处理</h3>
        </div>
        <p class="stat-value">{{ stats.unprocessed }}</p>
      </div>
      <div class="stat-card viewed">
        <div class="stat-header">
          <Eye class="w-6 h-6" />
          <h3>已查看</h3>
        </div>
        <p class="stat-value">{{ stats.viewed }}</p>
      </div>
      <div class="stat-card resolved">
        <div class="stat-header">
          <CheckCircle class="w-6 h-6" />
          <h3>已解决</h3>
        </div>
        <p class="stat-value">{{ stats.resolved }}</p>
      </div>
      <div class="stat-card total">
        <div class="stat-header">
          <Shield class="w-6 h-6" />
          <h3>告警总数</h3>
        </div>
        <p class="stat-value">{{ stats.total }}</p>
      </div>
    </div>

    <!-- 筛选和操作 -->
    <div class="controls-container">
      <div class="filters">
        <label class="filter-label">
          <Filter class="w-4 h-4" />
          <span>状态过滤:</span>
        </label>
        <select v-model="filterStatus" @change="fetchAlerts(1)" class="filter-select">
          <option value="">所有状态</option>
          <option value="unprocessed">未处理</option>
          <option value="viewed">已查看</option>
          <option value="resolved">已解决</option>
        </select>
      </div>
      <button @click="fetchAlerts(currentPage)" class="refresh-button">
        <RefreshCw class="w-4 h-4" />
        <span>刷新</span>
      </button>
    </div>

    <!-- 告警列表 -->
    <div class="alerts-list-container">
      <transition-group name="alert-list" tag="div" class="alerts-grid">
        <div v-for="alert in alerts" :key="alert.id" class="alert-card" :class="`status-${alert.status}`">
          <div class="card-header">
            <span class="event-type">
              <Tag class="w-3 h-3" />
              {{ alert.event_type }}
            </span>
            <span class="status-badge" :class="`status-${alert.status}`">{{ getStatusText(alert.status) }}</span>
          </div>
          <div class="card-body">
            <div class="media-preview" @click="showSnapshotModal(alert)">
              <img :src="getSnapshotUrl(alert.frame_snapshot_path)" alt="快照" @error="onImageError" />
              <div class="media-overlay">
                <Search class="w-6 h-6" />
              </div>
            </div>
            <div class="alert-details">
              <p class="details-text">{{ alert.details }}</p>
              <div class="timestamp">
                <Calendar class="w-3 h-3" />
                <span>{{ formatTimestamp(alert.timestamp) }}</span>
              </div>
            </div>
          </div>
          <div class="card-footer">
            <button @click="changeStatus(alert, 'viewed')" :disabled="alert.status === 'viewed' || alert.status === 'resolved'" class="action-btn viewed-btn">
              <Eye class="w-4 h-4" />
              <span>设为已读</span>
            </button>
            <button @click="changeStatus(alert, 'resolved')" :disabled="alert.status === 'resolved'" class="action-btn resolved-btn">
              <Check class="w-4 h-4" />
              <span>解决</span>
            </button>
          </div>
        </div>
      </transition-group>
      <div v-if="!alerts.length" class="no-data-placeholder">
        <ShieldOff class="w-16 h-16 text-gray-400" />
        <h3>当前无告警信息</h3>
        <p>所有系统均正常运行。</p>
      </div>
    </div>

    <!-- 分页 -->
    <div class="pagination-controls" v-if="totalPages > 1">
        <button @click="fetchAlerts(currentPage - 1)" :disabled="currentPage <= 1" class="page-button">
          <ChevronLeft class="w-4 h-4" />
          <span>上一页</span>
        </button>
        <div class="page-numbers">
          <span>第 {{ currentPage }} / {{ totalPages }} 页 (共 {{ totalItems }} 条)</span>
        </div>
        <button @click="fetchAlerts(currentPage + 1)" :disabled="currentPage >= totalPages" class="page-button">
          <span>下一页</span>
          <ChevronRight class="w-4 h-4" />
        </button>
    </div>

    <!-- 媒体查看模态框 -->
    <transition name="modal-fade">
      <div v-if="mediaModalVisible" class="media-modal-overlay" @click="hideMediaModal">
        <div class="media-modal-content" @click.stop>
          <div class="modal-header">
            <h3>告警详情 - {{ selectedAlert?.event_type }}</h3>
            <button class="close-button" @click="hideMediaModal">
              <X class="w-5 h-5" />
            </button>
          </div>
          <div class="modal-body">
            <div class="media-section">
              <h4>告警快照</h4>
              <img :src="getSnapshotUrl(selectedAlert?.frame_snapshot_path)" alt="告警快照" class="modal-image" @error="onImageError"/>
            </div>
            <div v-if="selectedAlert?.video_path" class="media-section">
              <h4>视频回放</h4>
              <video :src="getVideoUrl(selectedAlert?.video_path)" controls class="modal-video" preload="metadata">
                您的浏览器不支持视频播放
              </video>
            </div>
            <div class="info-section">
              <h4>详细信息</h4>
              <div class="info-grid">
                <div class="info-item">
                  <span class="info-label">告警时间</span>
                  <span class="info-value">{{ formatTimestamp(selectedAlert?.timestamp) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">告警状态</span>
                  <span class="info-value status-badge" :class="`status-${selectedAlert?.status}`">{{ getStatusText(selectedAlert?.status) }}</span>
                </div>
              </div>
              <div class="info-item full-width">
                <span class="info-label">告警描述</span>
                <p class="info-value">{{ selectedAlert?.details }}</p>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button @click="changeStatus(selectedAlert, 'viewed')" :disabled="selectedAlert?.status === 'viewed' || selectedAlert?.status === 'resolved'" class="modal-button viewed-btn">
              标记已读
            </button>
            <button @click="changeStatus(selectedAlert, 'resolved')" :disabled="selectedAlert?.status === 'resolved'" class="modal-button resolved-btn">
              标记解决
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import TopBar from '../components/TopBar.vue';

import {
  AlertTriangle, List, Clock, Eye, CheckCircle, Shield, Filter, RefreshCw,
  Tag, Search, Calendar, ShieldOff, ChevronLeft, ChevronRight, X, Check
} from 'lucide-vue-next';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000/api';
const SERVER_ROOT_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000';

const alerts = ref([]);
const currentPage = ref(1);
const totalPages = ref(1);
const totalItems = ref(0);
const filterStatus = ref('');
const mediaModalVisible = ref(false);
const selectedAlert = ref(null);
let refreshInterval = null;

const fetchAlerts = async (page = 1) => {
  try {
    // 使用数据库告警API (注意末尾的斜杠)
    let url = `${API_BASE_URL}/alerts/?page=${page}&per_page=10`;
    if (filterStatus.value) {
      url += `&status=${filterStatus.value}`;
    }
    
    const response = await fetch(url);
    const data = await response.json();
    
    if (data.alerts) {
      alerts.value = data.alerts;
      currentPage.value = data.page || page;
      totalPages.value = data.pages || 1;
      totalItems.value = data.total || data.alerts.length;
    } else {
      alerts.value = [];
      currentPage.value = 1;
      totalPages.value = 1;
      totalItems.value = 0;
    }
  } catch (error) {
    console.error('获取告警失败:', error);
    alerts.value = [];
  }
};

const changeStatus = async (alert, newStatus) => {
  try {
    const response = await fetch(`${API_BASE_URL}/alerts/${alert.id}/status`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ status: newStatus })
    });
    
    if (response.ok) {
      // 更新本地状态
      const index = alerts.value.findIndex(a => a.id === alert.id);
      if (index !== -1) {
        alerts.value[index].status = newStatus;
      }
      if (selectedAlert.value && selectedAlert.value.id === alert.id) {
        selectedAlert.value.status = newStatus;
      }
    } else {
      console.error('更新告警状态失败');
    }
  } catch (error) {
    console.error('更新告警状态失败:', error);
  }
};

const getSnapshotUrl = (snapshotPath) => {
  if (!snapshotPath) {
    return 'https://via.placeholder.com/200x120?text=No+Snapshot';
  }
  // 确保路径以 / 开头
  const path = snapshotPath.startsWith('/') ? snapshotPath : `/${snapshotPath}`;
  return `${SERVER_ROOT_URL}${path}`;
};

const getVideoUrl = (videoPath) => {
  if (!videoPath) return '';
  // 确保路径以 / 开头
  const path = videoPath.startsWith('/') ? videoPath : `/${videoPath}`;
  return `${SERVER_ROOT_URL}${path}`;
};

const onImageError = (event) => {
  event.target.src = 'https://via.placeholder.com/200x120?text=Image+Error';
};

// 在 script setup 部分添加日志记录和回放功能
const replayCache = new Map(); // 用于缓存回放数据

const fetchAlertReplay = async (alertId) => {
  // 如果缓存中已有此告警的回放数据，直接返回
  if (replayCache.has(alertId)) {
    return replayCache.get(alertId);
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/alerts/${alertId}/replay`);
    if (response.ok) {
      const data = await response.json();
      // 将结果存入缓存
      replayCache.set(alertId, data);
      return data;
    } else {
      console.error('获取告警回放失败');
      return null;
    }
  } catch (error) {
    console.error('获取告警回放失败:', error);
    return null;
  }
};

// 修改 playVideo 函数，优化逻辑
const playVideo = async (alert) => {
  // 如果已经有视频路径，直接显示
  if (alert.video_path) {
    selectedAlert.value = alert;
    mediaModalVisible.value = true;
    return;
  }
  
  // 尝试通过回放API获取视频路径
  const replayData = await fetchAlertReplay(alert.id);
  if (replayData && replayData.video_path) {
    // 更新告警对象的视频路径
    alert.video_path = replayData.video_path;
    selectedAlert.value = alert;
    mediaModalVisible.value = true;
  } else {
    alert('此告警没有可用的视频回放');
  }
};

// 修改 showSnapshotModal 函数，优化逻辑
const showSnapshotModal = async (alert) => {
  // 如果已经显示了同一个告警，不要重复获取数据
  if (selectedAlert.value && selectedAlert.value.id === alert.id) {
    return;
  }
  
  selectedAlert.value = alert;
  mediaModalVisible.value = true;
  
  // 异步获取回放数据，但不阻塞UI显示
  fetchAlertReplay(alert.id).then(replayData => {
    if (replayData && selectedAlert.value && selectedAlert.value.id === alert.id) {
      // 只在当前选中的告警没有变化时更新数据
      if (replayData.video_path && !selectedAlert.value.video_path) {
        selectedAlert.value.video_path = replayData.video_path;
      }
      if (replayData.frame_snapshot_path && !selectedAlert.value.frame_snapshot_path) {
        selectedAlert.value.frame_snapshot_path = replayData.frame_snapshot_path;
      }
    }
  });
};

const hideMediaModal = () => {
  mediaModalVisible.value = false;
  selectedAlert.value = null;
};

const formatTimestamp = (timestamp) => {
  if (!timestamp) return '';
  return new Date(timestamp).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

const getStatusText = (status) => {
  const statusMap = {
    'unprocessed': '未处理',
    'viewed': '已查看',
    'resolved': '已解决'
  };
  return statusMap[status] || status;
};

const router = useRouter();

// 新增：告警统计
const stats = computed(() => {
  const result = {
    unprocessed: 0,
    viewed: 0,
    resolved: 0,
    total: alerts.value.length
  };
  
  alerts.value.forEach(alert => {
    if (alert.status in result) {
      result[alert.status]++;
    }
  });
  
  return result;
});

// 新增：导航到系统日志
const goToSystemLogs = () => {
  router.push('/logs');
};

onMounted(() => {
  fetchAlerts(currentPage.value);
  // 每60秒刷新一次告警（从30秒改为60秒，减少请求频率）
  refreshInterval = setInterval(() => {
    fetchAlerts(currentPage.value);
  }, 60000);
});

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
});
</script>

<style scoped>
/* 基本页面样式 */
.alert-view-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding-bottom: 40px;
}

/* 页面标题 */
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
}

.title-text h1 {
  font-size: 28px;
  font-weight: 700;
}

.title-text p {
  opacity: 0.8;
  font-size: 14px;
}

.system-logs-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.15);
  color: white;
  border: none;
  cursor: pointer;
  transition: all 0.3s ease;
}

.system-logs-button:hover {
  background: rgba(255, 255, 255, 0.25);
}

/* 统计卡片 */
.stats-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 24px;
  padding: 0 32px;
  margin-bottom: 24px;
}

.stat-card {
  background: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.08);
  border-left: 5px solid;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.12);
}

.stat-card.unprocessed { border-color: #f59e0b; }
.stat-card.viewed { border-color: #3b82f6; }
.stat-card.resolved { border-color: #10b981; }
.stat-card.total { border-color: #6366f1; }

.stat-header {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #4b5563;
  margin-bottom: 8px;
}

.stat-header h3 {
  font-size: 16px;
  font-weight: 600;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  color: #1f2937;
}

/* 控制和筛选 */
.controls-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
  margin: 0 32px 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.05);
}

.filters {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.filter-select {
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  background: #f9fafb;
  font-size: 14px;
  outline: none;
}

.refresh-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
  border: none;
  cursor: pointer;
  transition: all 0.3s ease;
}

/* 告警卡片列表 */
.alerts-list-container {
  padding: 0 32px;
}

.alerts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 24px;
}

.alert-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  transition: all 0.3s ease;
  border-top: 5px solid;
}

.alert-card.status-unprocessed { border-color: #f59e0b; }
.alert-card.status-viewed { border-color: #3b82f6; }
.alert-card.status-resolved { border-color: #10b981; }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f8fafc;
}

.event-type {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 14px;
  color: #374151;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  color: white;
}

.status-badge.status-unprocessed { background: #f59e0b; }
.status-badge.status-viewed { background: #3b82f6; }
.status-badge.status-resolved { background: #10b981; }

.card-body {
  padding: 16px;
  display: flex;
  gap: 16px;
}

.media-preview {
  width: 100px;
  height: 100px;
  border-radius: 8px;
  overflow: hidden;
  position: relative;
  cursor: pointer;
  flex-shrink: 0;
}

.media-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.media-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.media-preview:hover .media-overlay {
  opacity: 1;
}

.alert-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.details-text {
  font-size: 14px;
  color: #4b5563;
  line-height: 1.5;
}

.timestamp {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #6b7280;
}

.card-footer {
  padding: 12px 16px;
  background: #f8fafc;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid #d1d5db;
  background: white;
  transition: all 0.3s ease;
}

.action-btn.viewed-btn:hover:not(:disabled) {
  background: #dbeafe;
  border-color: #3b82f6;
  color: #3b82f6;
}

.action-btn.resolved-btn:hover:not(:disabled) {
  background: #d1fae5;
  border-color: #10b981;
  color: #10b981;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 分页 */
.pagination-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 32px;
}

.page-button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  background: white;
  border: 1px solid #d1d5db;
  cursor: pointer;
}

.page-numbers {
  margin: 0 16px;
  font-size: 14px;
  color: #4b5563;
}

/* 无数据占位符 */
.no-data-placeholder {
  text-align: center;
  padding: 60px 0;
  color: #9ca3af;
  grid-column: 1 / -1;
}

/* 模态框样式 */
.media-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.media-modal-content {
  background: white;
  border-radius: 16px;
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: 16px 24px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.media-section {
  grid-column: 1 / -1;
}

.info-section {
  grid-column: 1 / -1;
}

.modal-image, .modal-video {
  width: 100%;
  border-radius: 8px;
  margin-top: 8px;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 8px;
}

.info-item {
  background: #f8fafc;
  padding: 12px;
  border-radius: 8px;
}

.info-label {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 4px;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.modal-button {
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  border: none;
  color: white;
}

.modal-button.viewed-btn { background: #3b82f6; }
.modal-button.resolved-btn { background: #10b981; }
</style>