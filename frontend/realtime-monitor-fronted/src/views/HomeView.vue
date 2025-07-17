<template>
  <div class="app-container">
    <!-- 引入顶部栏组件 -->
    <TopBar />

    <!-- 主内容区域 - 供其他页面填充 -->
    <main class="content-area">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
// 导入侧边栏组件
import Sidebar from '../components/Sidebar.vue'  // 假设侧边栏组件文件名为 Sidebar.vue，需根据实际路径调整
import { computed } from 'vue' 
import { useAuthStore } from '@/stores/auth'
import TopBar from '@/components/TopBar.vue' 


// 获取 Pinia 中的 auth 状态
const authStore = useAuthStore()
const router = useRouter()

// 解构用户信息和登录状态（响应式）
const { user, isAuthenticated, logout } = authStore
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #ffffff;
  color: #333333;
}

.content-area {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background-color: #ffffff;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .top-bar .button-group button span {
    display: none;
  }
  .top-bar .button-group button {
    padding: 8px;
  }
}
</style>