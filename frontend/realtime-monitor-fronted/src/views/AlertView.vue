<template>
  <div class="alert-info-page">
    <h1>告警中心</h1>

    <div class="alert-section control-section">
      <div class="filters">
        <label>
          状态过滤:
          <select v-model="filterStatus" @change="fetchAlerts(1)">
            <option value="">所有状态</option>
            <option value="unprocessed">未处理</option>
            <option value="viewed">已查看</option>
            <option value="resolved">已解决</option>
          </select>
        </label>
        <button @click="fetchAlerts(currentPage)" class="refresh-button">
          <i class="fa fa-refresh"></i> 刷新
        </button>
      </div>
      
      <div class="alerts-table-container">
        <table class="alerts-table">
          <thead>
            <tr>
              <th>快照/回放</th>
              <th>告警类型</th>
              <th>告警详情</th>
              <th>告警时间</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="alert in alerts" :key="alert.id" class="alert-row" :class="`status-${alert.status}`">
              <td class="alert-media">
                <!-- 快照图片 -->
                <div class="media-container">
                  <img :src="getSnapshotUrl(alert.frame_snapshot_path)" 
                       alt="告警快照" 
                       class="alert-snapshot" 
                       @click="showSnapshotModal(alert)"
                       @error="onImageError"/>
                  
                  <!-- 视频回放按钮 -->
                  <div class="media-controls">
                    <button v-if="alert.video_path" @click="playVideo(alert)" class="play-button">
                      <i class="fa fa-play"></i> 视频回放
                    </button>
                    <button @click="showSnapshotModal(alert)" class="view-button">
                      <i class="fa fa-search-plus"></i> 查看大图
                    </button>
                  </div>
                </div>
              </td>
              <td>
                <span class="event-type">{{ alert.event_type }}</span>
              </td>
              <td>
                <div class="alert-details">
                  <p>{{ alert.details }}</p>
                  <small v-if="alert.video_path" class="video-info">
                    <i class="fa fa-video-camera"></i> 包含视频记录
                  </small>
                </div>
              </td>
              <td>
                <div class="timestamp">
                  {{ formatTimestamp(alert.timestamp) }}
                </div>
              </td>
              <td>
                <span class="status-badge" :class="`status-${alert.status}`">
                  {{ getStatusText(alert.status) }}
                </span>
              </td>
              <td>
                <div class="action-buttons">
                  <button @click="changeStatus(alert, 'viewed')" 
                          :disabled="alert.status === 'viewed' || alert.status === 'resolved'" 
                          class="handle-button viewed-btn">
                    <i class="fa fa-eye"></i> 设为已读
                  </button>
                  <button @click="changeStatus(alert, 'resolved')" 
                          :disabled="alert.status === 'resolved'" 
                          class="handle-button resolved-btn">
                    <i class="fa fa-check"></i> 解决
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="!alerts.length" class="no-alert-row">
              <td colspan="6">
                <div class="no-data-placeholder">
                  <i class="fa fa-exclamation-triangle"></i>
                  <p>当前无告警信息</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <div class="pagination-controls" v-if="totalPages > 1">
        <button @click="fetchAlerts(currentPage - 1)" :disabled="currentPage <= 1" class="page-button">
          <i class="fa fa-chevron-left"></i> 上一页
        </button>
        <div class="page-numbers">
          <span>第 {{ currentPage }} / {{ totalPages }} 页 (共 {{ totalItems }} 条)</span>
        </div>
        <button @click="fetchAlerts(currentPage + 1)" :disabled="currentPage >= totalPages" class="page-button">
          下一页 <i class="fa fa-chevron-right"></i>
        </button>
      </div>
    </div>

    <!-- 媒体查看模态框 -->
    <div v-if="mediaModalVisible" class="media-modal" @click="hideMediaModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>告警详情 - {{ selectedAlert?.event_type }}</h3>
          <span class="close-button" @click="hideMediaModal">&times;</span>
        </div>
        
        <div class="modal-body">
          <div class="alert-info">
            <p><strong>告警时间:</strong> {{ formatTimestamp(selectedAlert?.timestamp) }}</p>
            <p><strong>告警详情:</strong> {{ selectedAlert?.details }}</p>
            <p><strong>状态:</strong> {{ getStatusText(selectedAlert?.status) }}</p>
          </div>
          
          <!-- 快照图片 -->
          <div class="media-section">
            <h4>告警快照</h4>
            <img :src="getSnapshotUrl(selectedAlert?.frame_snapshot_path)" 
                 alt="告警快照" 
                 class="modal-image"
                 @error="onImageError"/>
          </div>
          
          <!-- 视频回放 -->
          <div v-if="selectedAlert?.video_path" class="media-section">
            <h4>视频回放</h4>
            <video :src="getVideoUrl(selectedAlert?.video_path)" 
                   controls 
                   class="modal-video"
                   preload="metadata">
              您的浏览器不支持视频播放
            </video>
          </div>
        </div>
        
        <div class="modal-footer">
          <button @click="changeStatus(selectedAlert, 'viewed')" 
                  :disabled="selectedAlert?.status === 'viewed' || selectedAlert?.status === 'resolved'"
                  class="modal-button viewed-btn">
            <i class="fa fa-eye"></i> 标记已读
          </button>
          <button @click="changeStatus(selectedAlert, 'resolved')" 
                  :disabled="selectedAlert?.status === 'resolved'"
                  class="modal-button resolved-btn">
            <i class="fa fa-check"></i> 标记解决
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

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

const playVideo = (alert) => {
  if (!alert.video_path) return;
  selectedAlert.value = alert;
  mediaModalVisible.value = true;
};

const showSnapshotModal = (alert) => {
  selectedAlert.value = alert;
  mediaModalVisible.value = true;
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

onMounted(() => {
  fetchAlerts(currentPage.value);
  // 每30秒刷新一次告警
  refreshInterval = setInterval(() => {
    fetchAlerts(currentPage.value);
  }, 30000);
});

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
});
</script>

<style scoped>
.alert-info-page {
  padding: 20px;
  background-color: #f5f5f5;
  min-height: 100vh;
}

.alert-info-page h1 {
  color: #333;
  margin-bottom: 20px;
  font-size: 28px;
  font-weight: bold;
}

.alert-section {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.filters {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 20px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 6px;
}

.filters label {
  font-weight: 500;
  color: #555;
}

.filters select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  margin-left: 8px;
}

.refresh-button {
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: background-color 0.3s;
}

.refresh-button:hover {
  background: #0056b3;
}

.alerts-table-container {
  overflow-x: auto;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
}

.alerts-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.alerts-table th {
  background: #f8f9fa;
  padding: 15px 12px;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #e0e0e0;
  font-size: 14px;
}

.alerts-table td {
  padding: 15px 12px;
  border-bottom: 1px solid #f0f0f0;
  vertical-align: top;
}

.alert-row {
  transition: background-color 0.2s;
}

.alert-row:hover {
  background-color: #f8f9fa;
}

.alert-row.status-unprocessed {
  border-left: 4px solid #dc3545;
}

.alert-row.status-viewed {
  border-left: 4px solid #ffc107;
}

.alert-row.status-resolved {
  border-left: 4px solid #28a745;
}

.alert-media {
  width: 200px;
  min-width: 200px;
}

.media-container {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alert-snapshot {
  width: 180px;
  height: 120px;
  object-fit: cover;
  border-radius: 6px;
  cursor: pointer;
  border: 2px solid #e0e0e0;
  transition: border-color 0.3s, transform 0.2s;
}

.alert-snapshot:hover {
  border-color: #007bff;
  transform: scale(1.02);
}

.media-controls {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.play-button, .view-button {
  padding: 4px 8px;
  font-size: 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 3px;
  transition: background-color 0.3s;
}

.play-button {
  background: #28a745;
  color: white;
}

.play-button:hover {
  background: #218838;
}

.view-button {
  background: #6c757d;
  color: white;
}

.view-button:hover {
  background: #5a6268;
}

.event-type {
  font-weight: 600;
  color: #007bff;
  background: #e7f3ff;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 13px;
}

.alert-details p {
  margin: 0 0 5px 0;
  color: #333;
  line-height: 1.4;
}

.video-info {
  color: #28a745;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 3px;
}

.timestamp {
  font-size: 13px;
  color: #666;
  white-space: nowrap;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  text-align: center;
  display: inline-block;
  min-width: 70px;
}

.status-badge.status-unprocessed {
  background: #f8d7da;
  color: #721c24;
}

.status-badge.status-viewed {
  background: #fff3cd;
  color: #856404;
}

.status-badge.status-resolved {
  background: #d4edda;
  color: #155724;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.handle-button {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.3s;
  min-width: 80px;
  justify-content: center;
}

.handle-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.viewed-btn {
  background: #ffc107;
  color: #212529;
}

.viewed-btn:hover:not(:disabled) {
  background: #e0a800;
}

.resolved-btn {
  background: #28a745;
  color: white;
}

.resolved-btn:hover:not(:disabled) {
  background: #218838;
}

.no-data-placeholder {
  text-align: center;
  padding: 40px;
  color: #666;
}

.no-data-placeholder i {
  font-size: 48px;
  color: #ccc;
  margin-bottom: 15px;
  display: block;
}

.pagination-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
  padding: 15px 0;
}

.page-button {
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: background-color 0.3s;
}

.page-button:hover:not(:disabled) {
  background: #0056b3;
}

.page-button:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.page-numbers {
  font-weight: 500;
  color: #333;
}

/* 媒体模态框样式 */
.media-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 90vw;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 25px;
  border-bottom: 1px solid #e0e0e0;
  background: #f8f9fa;
  border-radius: 12px 12px 0 0;
}

.modal-header h3 {
  margin: 0;
  color: #333;
  font-size: 20px;
}

.close-button {
  font-size: 28px;
  font-weight: bold;
  color: #666;
  cursor: pointer;
  line-height: 1;
  transition: color 0.3s;
}

.close-button:hover {
  color: #333;
}

.modal-body {
  padding: 25px;
}

.alert-info {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.alert-info p {
  margin: 5px 0;
  color: #333;
}

.alert-info strong {
  color: #007bff;
}

.media-section {
  margin-bottom: 25px;
}

.media-section h4 {
  margin: 0 0 15px 0;
  color: #333;
  font-size: 16px;
  border-bottom: 2px solid #007bff;
  padding-bottom: 5px;
}

.modal-image {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.modal-video {
  width: 100%;
  max-width: 800px;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 20px 25px;
  border-top: 1px solid #e0e0e0;
  background: #f8f9fa;
  border-radius: 0 0 12px 12px;
}

.modal-button {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.3s;
  font-weight: 500;
}

.modal-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-button.viewed-btn {
  background: #ffc107;
  color: #212529;
}

.modal-button.viewed-btn:hover:not(:disabled) {
  background: #e0a800;
}

.modal-button.resolved-btn {
  background: #28a745;
  color: white;
}

.modal-button.resolved-btn:hover:not(:disabled) {
  background: #218838;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .alert-info-page {
    padding: 10px;
  }
  
  .filters {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  
  .alerts-table th,
  .alerts-table td {
    padding: 10px 8px;
    font-size: 13px;
  }
  
  .alert-media {
    width: 150px;
    min-width: 150px;
  }
  
  .alert-snapshot {
    width: 130px;
    height: 90px;
  }
  
  .action-buttons {
    flex-direction: row;
    flex-wrap: wrap;
  }
  
  .handle-button {
    font-size: 11px;
    padding: 4px 8px;
    min-width: 60px;
  }
  
  .modal-content {
    max-width: 95vw;
    margin: 10px;
  }
  
  .modal-header,
  .modal-body,
  .modal-footer {
    padding: 15px;
  }
}
</style>