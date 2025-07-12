<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
    <header class="top-bar">
      <div class="header-left">
        <h1>车站实时视频监控系统</h1>
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
      </div>
    </header>

    <div class="main-content">
      <!-- 引入侧边栏组件 -->
      <Sidebar :currentPath="$route.path" />
      
      <!-- 主内容区域 - 供其他页面填充 -->
      <main class="content-area">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
// 导入侧边栏组件
import Sidebar from '../components/Sidebar.vue'  // 假设侧边栏组件文件名为 Sidebar.vue，需根据实际路径调整

const router = useRouter()
const route = useRoute()
const role = ref('管理员')
const nickname = ref('张三')
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #121212; /* 深色主题背景 */
  color: #e0e0e0; /* 基础文本颜色 */
}

/* 顶部导航栏样式 */
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  height: 60px;
  background-color: #1e1e1e; /* 导航栏深色背景 */
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #e0e0e0;
}

.header-right {
  display: flex;
  align-items: center;
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
  border: 2px solid rgba(255, 255, 255, 0.3);
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.name-role h2 {
  margin: 0;
  font-size: 16px;
  color: #e0e0e0;
}

.name-role p {
  margin: 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

/* 主内容区域样式 */
.main-content {
  display: flex;
  flex: 1;
  height: calc(100vh - 60px);
}

/* 内容区域样式 */
.content-area {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background-color: #121212; /* 主内容区域深色背景 */
}

/* 响应式适配 - 仅保留与顶部导航和内容区域相关的适配 */
@media (max-width: 768px) {
  .header-left h1 {
    font-size: 16px;
  }
}
</style>