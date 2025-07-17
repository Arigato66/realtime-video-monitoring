<template>
  <div class="app-container">
    <!-- 引入顶部导航栏 -->
    <TopBar />
    
    <div class="about">
      <h1>实时视频监控系统</h1>
      <div class="content">
        <p>
          本系统是一个基于Flask和Vue的前后端分离实时视频监控应用，使用YOLOv8进行对象检测和追踪，能够检测危险区域内的物体并发出警报。
        </p>
        
        <h2>主要功能</h2>
        <ul>
          <li>实时视频监控与对象检测</li>
          <li>目标追踪与唯一ID分配</li>
          <li>危险区域定义与可视化</li>
          <li>危险区域入侵检测与告警</li>
          <li>可自定义安全距离和停留时间阈值</li>
          <li>支持上传视频或图片进行离线分析</li>
        </ul>
        
        <h2>技术栈</h2>
        <div class="tech-stack">
          <div class="tech-item">
            <h3>前端</h3>
            <ul>
              <li>Vue 3</li>
              <li>Vue Router</li>
              <li>Vite</li>
            </ul>
          </div>
          <div class="tech-item">
            <h3>后端</h3>
            <ul>
              <li>Flask</li>
              <li>Flask-CORS</li>
              <li>OpenCV</li>
              <li>YOLOv8</li>
            </ul>
          </div>
        </div>
        
        <h2>使用说明</h2>
        <ol>
          <li>选择视频源（摄像头或上传文件）</li>
          <li>点击"编辑区域"按钮自定义危险区域</li>
          <li>调整安全距离和警报阈值</li>
          <li>查看底部告警信息区域获取实时告警</li>
        </ol>
        
        <div class="footer">
          <p>© 2024 实时视频监控系统</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 引入TopBar组件（根据实际路径调整）
import TopBar from '@/components/TopBar.vue'
</script>

<style>
.app-container {
  min-height: 100vh;
  background-color: #ffffff;
}

.about {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px; /* 与顶部导航栏保持间距 */
}

h1 {
  text-align: center;
  margin-bottom: 30px;
  color: #2c3e50;
  margin-top: 20px; /* 增加与TopBar的距离 */
}

h2 {
  margin-top: 30px;
  margin-bottom: 15px;
  color: #2c3e50;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}

.content {
  background-color: white;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

p {
  line-height: 1.6;
  margin-bottom: 20px;
}

ul, ol {
  margin-bottom: 20px;
  padding-left: 20px;
}

li {
  margin-bottom: 10px;
  line-height: 1.4;
}

.tech-stack {
  display: flex;
  gap: 30px;
}

.tech-item {
  flex: 1;
}

.footer {
  margin-top: 50px;
  text-align: center;
  color: #777;
  font-size: 14px;
}
</style>