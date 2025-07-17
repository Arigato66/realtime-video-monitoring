<template>
  <header class="top-bar">
    <div class="header-left">
      <h1>车站实时视频监控系统</h1>
    </div>
    <div class="header-middle">
      <div class="button-group">
        <button @click="goToPage('/home')" :class="{ active: currentPath === '/home' }">
          <el-icon><House /></el-icon>
          <span>首页</span>
        </button>
        <span class="divider"></span>
        <button @click="goToPage('/face')" :class="{ active: currentPath === '/face' }">
          <el-icon><UserFilled /></el-icon>
          <span>入站人脸</span>
        </button>
        <span class="divider"></span>
        <button @click="goToPage('/monitor')" :class="{ active: currentPath === '/monitor' }">
          <el-icon><VideoCameraFilled /></el-icon>
          <span>监控大屏</span>
        </button>
        <span class="divider"></span>
        <button @click="goToPage('/alert')" :class="{ active: currentPath === '/alert' }">
          <el-icon><BellFilled /></el-icon>
          <span>警报处置</span>
        </button>
        <span class="divider"></span>
        <button @click="goToPage('/device')" :class="{ active: currentPath === '/device' }">
          <el-icon><Setting /></el-icon>
          <span>设备信息</span>
        </button>
        <span class="divider"></span>
        <button @click="goToPage('/about')" :class="{ active: currentPath === '/about' }">
          <el-icon><QuestionFilled /></el-icon>
          <span>关于系统</span>
        </button>
      </div>
    </div>
    <div class="header-right">
      <div class="profile-info">
        <div class="avatar">
          <img src="https://via.placeholder.com/100" alt="用户头像">
        </div>
        <div class="name-role">
          <h2>{{ nickname }}</h2>
          <p>{{ role }}</p>
        </div>
      </div>
      <div class="icon-group">
        <el-icon @click="goToPage('/settings')"><Setting /></el-icon>
        <el-icon @click="logout"><Logout /></el-icon>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
// 引入所需的 ElementPlus 图标
import { House, UserFilled, VideoCameraFilled, BellFilled, Setting, QuestionFilled} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const currentPath = ref(route.path)

const role = ref('管理员')
const nickname = ref('张三')

const goToPage = (path: string) => {
  router.push(path)
  currentPath.value = path
}

const logout = () => {
  localStorage.removeItem('authToken')
  localStorage.removeItem('userInfo')
  router.replace('/')
}
</script>

<style scoped>
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  height: 60px;
  background-color: #f8f9fa;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #333333;
}

.header-middle {
  display: flex;
  align-items: center;
}

.button-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.button-group button {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 8px 12px;
  background-color: transparent;
  color: #333333;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.button-group button:hover {
  background-color: #e9ecef;
  color: #007bff;
}

.button-group button.active {
  background-color: #007bff;
  color: white;
}

.divider {
  width: 1px;
  height: 20px;
  background-color: #ced4da;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
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
  border: 2px solid rgba(0, 0, 0, 0.1);
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.name-role h2 {
  margin: 0;
  font-size: 16px;
  color: #333333;
}

.name-role p {
  margin: 0;
  font-size: 12px;
  color: rgba(0, 0, 0, 0.6);
}

.icon-group {
  display: flex;
  align-items: center;
  gap: 15px;
}

.icon-group i {
  font-size: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.icon-group i:hover {
  color: #007bff;
}
</style>