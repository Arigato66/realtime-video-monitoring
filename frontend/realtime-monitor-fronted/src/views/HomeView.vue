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


const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()  // 获取 authStore 实例

// 响应式获取用户信息（登录/登出时自动更新）
const user = computed(() => authStore.user)

// 从用户信息中提取用户名（未登录时显示“未登录”）
const nickname = computed(() => user.value?.username || '未登录')

// 角色信息（如果后端返回角色，可从 user 中获取，这里先保持“管理员”）
const role = '管理员'  // 若后端返回角色，可改为：user.value?.role || '普通用户'
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