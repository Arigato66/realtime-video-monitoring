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

<script setup>
import TopBar from '../components/TopBar.vue' // 根据实际路径调整
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