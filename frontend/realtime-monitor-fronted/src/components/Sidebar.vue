<template>
  <aside class="sidebar">
    <div class="sidebar-section">
      <h3>操作选项</h3>
      <div class="button-group">
        <button @click="goToFaceRecognitionPage" :class="{ active: currentPath === '/face' }">入站人脸</button>
        <button @click="goToMonitorPage" :class="{ active: currentPath === '/monitor' }">监控大屏</button>
        <button @click="goToAlertPage" :class="{ active: currentPath === '/alert' }">警报处置</button>
        <button @click="goToDevicePage" :class="{ active: currentPath === '/device' }">设备信息</button>
      </div>
    </div>
    
    <div class="sidebar-section">
      <h3>菜单</h3>
      <div class="button-group">
        <button @click="goToAboutPage" :class="{ active: currentPath === '/about' }">关于系统</button>
        <button @click="logout" class="logout-btn">退出登录</button>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, defineProps, defineEmits } from 'vue'
import { useRouter } from 'vue-router'

// 接收当前路由路径作为参数
const props = defineProps<{
  currentPath: string
}>()

const router = useRouter()

// 路由跳转方法
const goToMonitorPage = () => {
  router.push('/monitor')
}

const goToAlertPage = () => {
  router.push('/alert')
}

const goToFaceRecognitionPage = () => {
  router.push('/face')
}

const goToAboutPage = () => {
  router.push('/about')
}

const goToDevicePage = () => {
  router.push('/device')
}

const logout = () => {
  localStorage.removeItem('authToken')
  localStorage.removeItem('userInfo')
  router.replace('/')
}
</script>

<style scoped>
.sidebar {
  width: 220px;
  background-color: #1e1e1e;
  border-right: 1px solid #333;
  padding: 20px 0;
  overflow-y: auto;
}

.sidebar-section {
  margin-bottom: 30px;
  padding: 0 15px;
}

.sidebar-section h3 {
  margin: 0 0 15px 10px;
  color: #ccc;
  font-size: 16px;
  font-weight: 600;
  padding-bottom: 8px;
  border-bottom: 1px solid #333;
}

.button-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.button-group button {
  width: 100%;
  padding: 12px 15px;
  background-color: transparent;
  color: #ccc;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  text-align: left;
  transition: all 0.3s ease;
}

.button-group button:hover {
  background-color: rgba(0, 123, 255, 0.2);
  color: #007bff;
}

.button-group button.active {
  background-color: #007bff;
  color: white;
}

.logout-btn {
  margin-top: 10px;
  color: #f44336 !important;
}

.logout-btn:hover {
  background-color: rgba(244, 67, 54, 0.1) !important;
  color: #f44336 !important;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .sidebar {
    width: 60px;
    padding: 20px 0;
  }

  .sidebar-section h3 {
    display: none;
  }

  .button-group button {
    justify-content: center;
    text-align: center;
    padding: 12px 0;
    font-size: 0; /* 隐藏文字 */
    position: relative;
  }
  
  /* 可添加图标替代文字（示例） */
  .button-group button::after {
    content: attr(data-icon);
    font-size: 16px;
  }
}
</style>