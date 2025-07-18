<template>
  <div class="logs-page">
    <h1>系统监控日志</h1>

    <div class="logs-section control-section">
      <div class="filters">
        <div class="filter-group">
          <label>
            日志级别:
            <select v-model="filterLevel">
              <option value="">所有级别</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </label>
        </div>
        
        <div class="filter-group">
          <label>
            模块:
            <input type="text" v-model="filterModule" placeholder="输入模块名称">
          </label>
        </div>
        
        <div class="filter-group">
          <label>
            开始时间:
            <input type="datetime-local" v-model="startDate">
          </label>
        </div>
        
        <div class="filter-group">
          <label>
            结束时间:
            <input type="datetime-local" v-model="endDate">
          </label>
        </div>
        
        <button @click="fetchLogs(1)" class="search-button" :disabled="isLoading">
          <i class="fa fa-search"></i> {{ isLoading ? '加载中...' : '搜索' }}
        </button>
        
        <button @click="resetFilters" class="reset-button" :disabled="isLoading">
          <i class="fa fa-refresh"></i> 重置
        </button>
      </div>
      
      <!-- 添加加载指示器 -->
      <div v-if="isLoading" class="loading-indicator">
        <div class="spinner"></div>
        <span>加载中...</span>
      </div>
      
      <div class="logs-table-container">
        <table class="logs-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>级别</th>
              <th>模块</th>
              <th>消息</th>
              <th>详情</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in logs" :key="log.log_id" class="log-row" :class="`level-${log.log_level.toLowerCase()}`">
              <td>
                <div class="timestamp">
                  {{ formatTimestamp(log.log_time) }}
                </div>
              </td>
              <td>
                <span class="level-badge" :class="`level-${log.log_level.toLowerCase()}`">
                  {{ log.log_level }}
                </span>
              </td>
              <td>
                <span class="module-name">{{ log.module }}</span>
              </td>
              <td>
                <div class="log-message">{{ log.message }}</div>
              </td>
              <td>
                <button v-if="log.details" @click="showDetails(log)" class="details-button">
                  <i class="fa fa-info-circle"></i> 查看
                </button>
                <span v-else>-</span>
              </td>
            </tr>
            <tr v-if="!logs.length" class="no-log-row">
              <td colspan="5">
                <div class="no-data-placeholder">
                  <i class="fa fa-exclamation-triangle"></i>
                  <p>没有找到符合条件的日志</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <div class="pagination-controls" v-if="totalPages > 1">
        <button @click="fetchLogs(currentPage - 1)" :disabled="currentPage <= 1" class="page-button">
          <i class="fa fa-chevron-left"></i> 上一页
        </button>
        <div class="page-numbers">
          <span>第 {{ currentPage }} / {{ totalPages }} 页 (共 {{ totalItems }} 条)</span>
        </div>
        <button @click="fetchLogs(currentPage + 1)" :disabled="currentPage >= totalPages" class="page-button">
          下一页 <i class="fa fa-chevron-right"></i>
        </button>
      </div>
    </div>

    <!-- 日志详情模态框 -->
    <div v-if="detailsModalVisible" class="details-modal" @click="hideDetailsModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>日志详情</h3>
          <span class="close-button" @click="hideDetailsModal">&times;</span>
        </div>
        
        <div class="modal-body">
          <div class="log-info">
            <p><strong>时间:</strong> {{ formatTimestamp(selectedLog?.log_time) }}</p>
            <p><strong>级别:</strong> 
              <span class="level-badge" :class="`level-${selectedLog?.log_level.toLowerCase()}`">
                {{ selectedLog?.log_level }}
              </span>
            </p>
            <p><strong>模块:</strong> {{ selectedLog?.module }}</p>
            <p><strong>消息:</strong> {{ selectedLog?.message }}</p>
          </div>
          
          <div class="details-section">
            <h4>详细信息</h4>
            <pre class="details-content">{{ selectedLog?.details }}</pre>
          </div>
          
          <div v-if="selectedLog?.user_id" class="user-section">
            <p><strong>操作用户ID:</strong> {{ selectedLog?.user_id }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000/api';

// 状态变量
const logs = ref([]);
const currentPage = ref(1);
const totalPages = ref(1);
const totalItems = ref(0);
const filterLevel = ref('');
const filterModule = ref('');
const startDate = ref('');
const endDate = ref('');
const detailsModalVisible = ref(false);
const selectedLog = ref(null);

// 添加加载状态和节流控制
const isLoading = ref(false);
let lastFetchTime = 0;
const FETCH_COOLDOWN = 2000; // 2秒内不重复请求

// 格式化ISO时间字符串为本地时间
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

// 格式化日期时间为ISO字符串
const formatDateForApi = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toISOString();
};

// 获取日志列表
const fetchLogs = async (page = 1) => {
  // 节流控制：如果距离上次请求不足2秒且不是强制刷新，则跳过
  const now = Date.now();
  if (isLoading.value || (now - lastFetchTime < FETCH_COOLDOWN)) {
    return;
  }
  
  isLoading.value = true;
  lastFetchTime = now;
  
  try {
    let url = `${API_BASE_URL}/system-logs/?page=${page}&per_page=10`;
    
    if (filterLevel.value) {
      url += `&level=${filterLevel.value}`;
    }
    
    if (filterModule.value) {
      url += `&module=${filterModule.value}`;
    }
    
    if (startDate.value) {
      url += `&start_date=${encodeURIComponent(formatDateForApi(startDate.value))}`;
    }
    
    if (endDate.value) {
      url += `&end_date=${encodeURIComponent(formatDateForApi(endDate.value))}`;
    }
    
    const response = await fetch(url);
    const data = await response.json();
    
    if (data.logs) {
      logs.value = data.logs;
      currentPage.value = data.current_page || page;
      totalPages.value = data.pages || 1;
      totalItems.value = data.total || data.logs.length;
    } else {
      logs.value = [];
      currentPage.value = 1;
      totalPages.value = 1;
      totalItems.value = 0;
    }
  } catch (error) {
    console.error('获取日志失败:', error);
    logs.value = [];
  } finally {
    isLoading.value = false;
  }
};

// 重置过滤条件
const resetFilters = () => {
  filterLevel.value = '';
  filterModule.value = '';
  startDate.value = '';
  endDate.value = '';
  fetchLogs(1);
};

// 显示日志详情
const showDetails = (log) => {
  selectedLog.value = log;
  detailsModalVisible.value = true;
};

// 隐藏日志详情模态框
const hideDetailsModal = () => {
  detailsModalVisible.value = false;
  selectedLog.value = null;
};

// 组件挂载时获取日志
onMounted(() => {
  fetchLogs(1);
});
</script>

<style scoped>
.logs-page {
  padding: 20px;
  background-color: #f5f5f5;
  min-height: 100vh;
}

.logs-page h1 {
  color: #333;
  margin-bottom: 20px;
  font-size: 28px;
  font-weight: bold;
}

.logs-section {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  margin-bottom: 20px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 6px;
}

.filter-group {
  display: flex;
  align-items: center;
}

.filters label {
  font-weight: 500;
  color: #555;
  margin-right: 8px;
}

.filters select,
.filters input[type="text"],
.filters input[type="datetime-local"] {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.search-button,
.reset-button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: background-color 0.3s;
}

.search-button {
  background: #007bff;
  color: white;
}

.search-button:hover {
  background: #0056b3;
}

.reset-button {
  background: #6c757d;
  color: white;
}

.reset-button:hover {
  background: #5a6268;
}

.logs-table-container {
  overflow-x: auto;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
}

.logs-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.logs-table th {
  background: #f8f9fa;
  padding: 15px 12px;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #e0e0e0;
  font-size: 14px;
}

.logs-table td {
  padding: 15px 12px;
  border-bottom: 1px solid #f0f0f0;
  vertical-align: top;
}

.log-row {
  transition: background-color 0.2s;
}

.log-row:hover {
  background-color: #f8f9fa;
}

.log-row.level-info {
  border-left: 4px solid #17a2b8;
}

.log-row.level-warning {
  border-left: 4px solid #ffc107;
}

.log-row.level-error {
  border-left: 4px solid #dc3545;
}

.log-row.level-critical {
  border-left: 4px solid #721c24;
}

.timestamp {
  font-size: 13px;
  color: #666;
  white-space: nowrap;
}

.level-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  text-align: center;
  display: inline-block;
  min-width: 70px;
}

.level-badge.level-info {
  background: #d1ecf1;
  color: #0c5460;
}

.level-badge.level-warning {
  background: #fff3cd;
  color: #856404;
}

.level-badge.level-error {
  background: #f8d7da;
  color: #721c24;
}

.level-badge.level-critical {
  background: #721c24;
  color: #fff;
}

.module-name {
  font-weight: 500;
  color: #495057;
  background: #e9ecef;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.log-message {
  color: #333;
  line-height: 1.4;
}

.details-button {
  padding: 4px 8px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 3px;
  transition: background-color 0.3s;
}

.details-button:hover {
  background: #5a6268;
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

/* 详情模态框样式 */
.details-modal {
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
  width: 600px;
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

.log-info {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.log-info p {
  margin: 5px 0;
  color: #333;
}

.log-info strong {
  color: #007bff;
}

.details-section {
  margin-bottom: 20px;
}

.details-section h4 {
  margin: 0 0 15px 0;
  color: #333;
  font-size: 16px;
  border-bottom: 2px solid #007bff;
  padding-bottom: 5px;
}

.details-content {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  white-space: pre-wrap;
  font-family: monospace;
  font-size: 14px;
  color: #333;
  max-height: 300px;
  overflow-y: auto;
}

.user-section {
  padding: 10px 0;
  border-top: 1px solid #e0e0e0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .logs-page {
    padding: 10px;
  }
  
  .filters {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  
  .filter-group {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .logs-table th,
  .logs-table td {
    padding: 10px 8px;
    font-size: 13px;
  }
  
  .modal-content {
    width: 95vw;
    margin: 10px;
  }
  
  .modal-header,
  .modal-body {
    padding: 15px;
  }
}

/* 添加加载指示器样式 */
.loading-indicator {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  color: #666;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 3px solid rgba(0, 123, 255, 0.3);
  border-radius: 50%;
  border-top-color: #007bff;
  animation: spin 1s linear infinite;
  margin-right: 10px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style> 