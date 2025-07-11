<template>
  <div class="alert-info-page">
    <h1>实时告警信息列表</h1>

    <div class="alert-section control-section">
      <!-- 告警统计 -->
      <div class="alert-stats">
        <span>当前共有 <strong>{{ alerts.length }}</strong> 条告警信息</span>
      </div>
      
      <!-- 告警列表 -->
      <div class="alerts-table-container">
        <table class="alerts-table">
          <thead>
            <tr>
              <th>监控回放</th>
              <th>告警类型</th>
              <th>告警地点</th>
              <th>告警时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="alert in currentPageAlerts" :key="alert.id" class="alert-row">
              <td class="alert-video">
                <img :src="alert.snapshotUrl" alt="告警快照" class="alert-snapshot" />
                <button @click="playVideo(alert.videoUrl)" class="play-button">
                  <i class="fa fa-play"></i> 回放
                </button>
              </td>
              <td>{{ alert.type }}</td>
              <td>{{ alert.location }}</td>
              <td>{{ alert.time }}</td>
              <td>
                <button @click="handleAlert(alert.id)" class="handle-button">
                  <i class="fa fa-wrench"></i> 处置
                </button>
              </td>
            </tr>
            <tr v-if="!currentPageAlerts.length" class="no-alert-row">
              <td colspan="5">
                <div class="video-placeholder">
                  <p>当前无告警信息</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <!-- 分页控件 -->
      <div class="pagination-controls" v-if="totalPages > 1">
        <button @click="prevPage" :disabled="currentPage === 1" class="page-button">
          <i class="fa fa-chevron-left"></i> 上一页
        </button>
        
        <div class="page-numbers">
          <button 
            v-for="page in pageRange" 
            :key="page" 
            :class="{ active: page === currentPage }"
            @click="goToPage(page)"
            class="page-number"
          >
            {{ page }}
          </button>
        </div>
        
        <button @click="nextPage" :disabled="currentPage === totalPages" class="page-button">
          下一页 <i class="fa fa-chevron-right"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { useRouter } from 'vue-router';

// API端点设置
// 使用相对路径替代硬编码的服务器地址
const API_BASE_URL = '/api';

// 状态变量
const alerts = ref([]);
const currentPage = ref(1);
const pageSize = ref(5);
const router = useRouter();

// 生成测试用例数据
const generateTestAlerts = () => {
  // 模拟不同类型的告警
  const alertTypes = [
    '区域入侵',
    '人员聚集',
    '长时间停留',
    '异常行为',
    '物品遗留'
  ];
  
  // 模拟不同监控地点
  const locations = [
    '东门入口通道',
    '二号仓库A区',
    '主楼大厅左侧',
    '地下车库B3区域',
    '南门安检处',
    '办公楼一层走廊',
    '货运通道闸机口'
  ];
  
  // 生成12条测试数据（用于测试分页）
  return Array.from({ length: 12 }, (_, i) => {
    const now = new Date();
    // 时间错开，模拟不同时间的告警
    const alertTime = new Date(now.getTime() - i * 60000 * (Math.floor(Math.random() * 10) + 1));
    
    return {
      id: `alert-${i + 1001}`,
      type: alertTypes[Math.floor(Math.random() * alertTypes.length)],
      location: locations[Math.floor(Math.random() * locations.length)],
      time: alertTime.toLocaleString(),
      // 使用随机图片作为快照
      snapshotUrl: `https://picsum.photos/seed/alert${i}/200/120`,
      videoUrl: `${SERVER_ROOT_URL}/videos/alert-${i + 1001}.mp4`
    };
  });
};

// 计算属性
const totalPages = computed(() => {
  return Math.ceil(alerts.value.length / pageSize.value);
});

const currentPageAlerts = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return alerts.value.slice(start, end);
});

const pageRange = computed(() => {
  // 只显示当前页附近的页码
  let start = Math.max(1, currentPage.value - 2);
  let end = Math.min(totalPages.value, start + 4);
  
  // 调整起始页码，确保显示5个页码
  if (end - start < 4) {
    start = Math.max(1, end - 4);
  }
  
  return Array.from({ length: end - start + 1 }, (_, i) => start + i);
});

// 定期轮询告警信息（开发阶段使用测试数据）
let alertPollingInterval = null;

const startAlertPolling = () => {
  // 先清除之前的轮询
  if (alertPollingInterval) {
    clearInterval(alertPollingInterval);
  }

  // 开发阶段直接使用测试数据
  alerts.value = generateTestAlerts();
  
  // 模拟定期更新（每30秒刷新一次测试数据）
  alertPollingInterval = setInterval(() => {
    // 随机更新一条数据，模拟新告警
    if (alerts.value.length > 0) {
      const randomIndex = Math.floor(Math.random() * alerts.value.length);
      const updatedAlerts = [...alerts.value];
      updatedAlerts[randomIndex] = {
        ...updatedAlerts[randomIndex],
        time: new Date().toLocaleString()
      };
      alerts.value = updatedAlerts;
    }
  }, 30000);
};

// 分页控制方法
const prevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--;
  }
};

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++;
  }
};

const goToPage = (page) => {
  currentPage.value = page;
};

// 操作方法
const handleAlert = (alertId) => {
  // 跳转到告警处置页面，携带告警ID
  router.push({ name: 'AlertHandle', params: { id: alertId } });
};

const playVideo = (videoUrl) => {
  // 开发阶段显示提示
  alert(`播放告警视频: ${videoUrl}\n(实际环境中会打开视频播放器)`);
  // 实际环境中使用：window.open(videoUrl, '_blank');
};

// 生命周期钩子
onMounted(() => {
  startAlertPolling();
});

onUnmounted(() => {
  if (alertPollingInterval) {
    clearInterval(alertPollingInterval);
  }
});
</script>

<style>
/* 样式部分与之前保持一致 */
.alert-info-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

h1 {
  text-align: center;
  margin-bottom: 30px;
  color: #2c3e50;
}

h3 {
  margin-bottom: 10px;
  color: #2c3e50;
  font-size: 16px;
}

/* 统一控制区域样式 */
.control-section {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f9f9f9;
  border-radius: 5px;
  border: 1px solid #eee;
}

.alert-stats {
  margin-bottom: 15px;
  padding: 10px;
  background-color: #f2f2f2;
  border-radius: 4px;
  font-size: 14px;
}

/* 表格容器样式 */
.alerts-table-container {
  overflow-x: auto;
  margin-bottom: 20px;
}

.alerts-table {
  width: 100%;
  border-collapse: collapse;
  background-color: #fff;
}

.alerts-table th, .alerts-table td {
  padding: 10px;
  border: 1px solid #ddd;
  text-align: left;
}

.alerts-table th {
  background-color: #f2f2f2;
  font-weight: 600;
}

.alert-row {
  transition: background-color 0.2s;
}

.alert-row:hover {
  background-color: #f9f9f9;
}

/* 告警视频列样式 */
.alert-video {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alert-snapshot {
  max-width: 100px;
  max-height: 60px;
  object-fit: cover;
  border-radius: 3px;
  border: 1px solid #ddd;
}

/* 按钮样式统一 */
.play-button, .handle-button {
  padding: 8px 12px;
  background-color: #2196F3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  width: fit-content;
}

.play-button:hover, .handle-button:hover {
  background-color: #0b7dda;
}

.handle-button {
  background-color: #4CAF50;
}

.handle-button:hover {
  background-color: #45a049;
}

/* 无数据状态样式 */
.no-alert-row td {
  height: 150px; /* 保持表格高度 */
  vertical-align: middle;
}

.video-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  height: 100%;
}

/* 分页控件样式 */
.pagination-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  margin-top: 20px;
}

.page-button, .page-number {
  padding: 8px 12px;
  background-color: #f2f2f2;
  color: #333;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.page-button:hover, .page-number:hover:not(.active) {
  background-color: #e0e0e0;
}

.page-button:disabled {
  background-color: #f5f5f5;
  color: #aaa;
  cursor: not-allowed;
}

.page-number.active {
  background-color: #2196F3;
  color: white;
}

.page-numbers {
  display: flex;
  gap: 5px;
}

/* 响应式调整 */
@media (max-width: 1024px) {
  .alerts-table th, .alerts-table td {
    padding: 8px;
    font-size: 13px;
  }
  
  .alert-snapshot {
    max-width: 80px;
    max-height: 50px;
  }
}
</style>