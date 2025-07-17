<template>
  <div class="device-page">
    <h1>设备信息列表</h1>

    <div class="device-section control-section">
      <!-- 设备统计 -->
      <div class="device-stats">
        <span>当前共有 <strong>{{ devices.length }}</strong> 台设备 | 
        正常: <span class="status-normal">{{ normalCount }}</span> 台 | 
        异常: <span class="status-abnormal">{{ abnormalCount }}</span> 台</span>
      </div>
      
      <!-- 设备列表 -->
      <div class="devices-table-container">
        <table class="devices-table">
          <thead>
            <tr>
              <th>设备ID</th>
              <th>设备型号</th>
              <th>设备位置</th>
              <th>设备年限</th>
              <th>设备状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="device in currentPageDevices" :key="device.id" class="device-row">
              <td>{{ device.id }}</td>
              <td>{{ device.model }}</td>
              <td>{{ device.location }}</td>
              <td>{{ device.years }} 年</td>
              <td>
                <span :class="`status-badge ${device.status === '正常' ? 'status-normal' : 'status-abnormal'}`">
                  {{ device.status }}
                </span>
              </td>
              <td>
                <button @click="viewDeviceStream(device.id)" class="view-button">
                  <i class="fa fa-eye"></i> 查看
                </button>
              </td>
            </tr>
            <tr v-if="!currentPageDevices.length" class="no-device-row">
              <td colspan="6">
                <div class="video-placeholder">
                  <p>当前无设备信息</p>
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

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';

// 定义设备信息类型接口（解决TS类型报错）
interface Device {
  id: string;
  model: string;
  location: string;
  years: string;
  status: '正常' | '异常';
  streamUrl: string;
}

// 删除这些重复的声明（第81-83行）：
// const SERVER_ROOT_URL = 'http://localhost:5000';
// const API_BASE_URL = `${SERVER_ROOT_URL}/api`;

// API端点设置（修改后）
const SERVER_ROOT_URL = ''; // 使用相对路径
const API_BASE_URL = '/api';

// 状态变量（指定类型为Device数组）
const devices = ref<Device[]>([]);
const currentPage = ref(1);
const pageSize = ref(6); // 每页显示6条
const router = useRouter();

// 生成测试用例数据
const generateTestDevices = (): Device[] => {
  // 设备型号库
  const models = [
    '海康威视DS-2CD3T46WD-I3', 
    '大华DH-IPC-HFW4433M-I2', 
    '宇视IPC323L-IR3', 
    '华为C200',
    '天地伟业TC-NC9400S3E',
    '安讯士AXIS P1425-LE'
  ];
  
  // 设备位置库
  const locations = [
    '东门入口通道', 
    '二号仓库A区', 
    '主楼大厅左侧', 
    '地下车库B3区域',
    '南门安检处', 
    '办公楼一层走廊', 
    '货运通道闸机口', 
    '候车大厅A区',
    '候车大厅B区', 
    '出站口通道', 
    '站台1号区域', 
    '站台2号区域',
    '售票厅C窗口',
    '行李寄存处'
  ];
  
  // 生成18条测试数据（用于测试分页）
  return Array.from({ length: 18 }, (_, i) => ({
    id: `CAM-${1001 + i}`,
    model: models[Math.floor(Math.random() * models.length)],
    location: locations[Math.floor(Math.random() * locations.length)],
    years: (Math.random() * 5 + 0.5).toFixed(1), // 0.5-5.5年
    status: Math.random() > 0.15 ? '正常' : '异常', // 15%概率异常
    streamUrl: `${API_BASE_URL}/stream/${1001 + i}` // 实时流地址
  }));
};

// 计算属性
const totalPages = computed(() => {
  return Math.ceil(devices.value.length / pageSize.value);
});

const currentPageDevices = computed<Device[]>(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return devices.value.slice(start, end);
});

const pageRange = computed<number[]>(() => {
  let start = Math.max(1, currentPage.value - 2);
  let end = Math.min(totalPages.value, start + 4);
  if (end - start < 4) start = Math.max(1, end - 4);
  return Array.from({ length: end - start + 1 }, (_, i) => start + i);
});

// 状态统计
const normalCount = computed<number>(() => {
  return devices.value.filter(d => d.status === '正常').length;
});

const abnormalCount = computed<number>(() => {
  return devices.value.filter(d => d.status === '异常').length;
});

// 分页控制
const prevPage = () => {
  if (currentPage.value > 1) currentPage.value--;
};

const nextPage = () => {
  if (currentPage.value < totalPages.value) currentPage.value++;
};

const goToPage = (page: number) => {
  currentPage.value = page;
};

// 查看实时画面
const viewDeviceStream = (deviceId: string) => {
  router.push(`/monitor?deviceId=${deviceId}`);
};

// 初始化 - 加载测试数据
onMounted(() => {
  // 开发阶段加载测试数据
  devices.value = generateTestDevices();
  
  // 实际环境中可替换为API请求
  /*
  fetch(`${API_BASE_URL}/devices`)
    .then(res => res.json())
    .then(data => devices.value = data.devices || [])
    .catch(err => console.error('获取设备信息失败:', err));
  */
});
</script>

<style>
.device-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

h1 {
  text-align: center;
  margin-bottom: 30px;
  color: #2c3e50;
}

h2 {
  margin-bottom: 15px;
  color: #2c3e50;
}

/* 统一控制区域 */
.control-section {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f9f9f9;
  border-radius: 5px;
  border: 1px solid #eee;
}

/* 统计区域 */
.device-stats {
  margin-bottom: 15px;
  padding: 10px;
  background-color: #f2f2f2;
  border-radius: 4px;
  font-size: 14px;
}

.status-normal {
  color: #4CAF50;
  font-weight: bold;
}

.status-abnormal {
  color: #f44336;
  font-weight: bold;
}

/* 表格样式 */
.devices-table-container {
  overflow-x: auto;
  margin-bottom: 20px;
}

.devices-table {
  width: 100%;
  border-collapse: collapse;
  background-color: #fff;
}

.devices-table th, .devices-table td {
  padding: 12px 10px;
  border: 1px solid #ddd;
  text-align: left;
}

.devices-table th {
  background-color: #f2f2f2;
  font-weight: 600;
}

.device-row {
  transition: background-color 0.2s;
}

.device-row:hover {
  background-color: #f9f9f9;
}

/* 状态标签 */
.status-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
}

.status-badge.status-normal {
  background-color: #e8f5e9;
  color: #2e7d32;
}

.status-badge.status-abnormal {
  background-color: #ffebee;
  color: #c62828;
}

/* 按钮样式 */
.view-button {
  padding: 8px 12px;
  background-color: #2196F3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.view-button:hover {
  background-color: #0b7dda;
}

/* 无数据状态 */
.no-device-row td {
  height: 150px;
  vertical-align: middle;
}

.video-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  height: 100%;
}

/* 分页样式 */
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
  .devices-table th, .devices-table td {
    padding: 8px;
    font-size: 13px;
  }
}
</style>