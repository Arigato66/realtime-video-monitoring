<template>
  <div class="video-window">
    <div class="video-header">
      <h4>{{ stream.name }}</h4>
      <div class="video-controls">
        <span class="fps">FPS: {{ currentFps }}</span>
        <button @click="$emit('close')" class="close-btn">×</button>
      </div>
    </div>
    
    <div class="video-content">
      <!-- 视频显示区域 -->
      <div class="video-display">
        <img v-if="currentFrame" 
             :src="`data:image/jpeg;base64,${currentFrame}`" 
             :alt="stream.name"
             class="video-frame" />
        <div v-else class="no-video">
          <p>等待视频数据...</p>
        </div>
      </div>
      
      <!-- AI分析结果显示 -->
      <div class="ai-results" v-if="aiResults">
        <div class="detection-count">
          <span>检测到: {{ detectionCount }} 个目标</span>
        </div>
        
        <div class="alerts" v-if="alerts.length > 0">
          <div v-for="alert in alerts" :key="alert.id" 
               :class="['alert', alert.severity]">
            {{ alert.message }}
          </div>
        </div>
        
        <div class="statistics">
          <div v-for="(value, key) in statistics" :key="key">
            {{ key }}: {{ value }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref, watch } from 'vue'
import { useStreamStore } from '@/stores/stream'

export default {
  name: 'VideoWindow',
  props: {
    stream: {
      type: Object,
      required: true
    }
  },
  emits: ['close'],
  setup(props) {
    const streamStore = useStreamStore()
    
    const streamData = computed(() => 
      streamStore.getStreamData(props.stream.id)
    )
    
    const currentFrame = computed(() => 
      streamData.value?.frame || null
    )
    
    const currentFps = computed(() => 
      streamData.value?.fps || 0
    )
    
    const aiResults = computed(() => 
      streamData.value?.ai_results || null
    )
    
    const detectionCount = computed(() => 
      aiResults.value?.detections?.length || 0
    )
    
    const alerts = computed(() => 
      aiResults.value?.alerts || []
    )
    
    const statistics = computed(() => 
      aiResults.value?.statistics || {}
    )
    
    return {
      currentFrame,
      currentFps,
      aiResults,
      detectionCount,
      alerts,
      statistics
    }
  }
}
</script>

<style scoped>
.video-window {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.video-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
}

.video-header h4 {
  margin: 0;
  font-size: 14px;
}

.video-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.fps {
  font-size: 12px;
  color: #6c757d;
}

.close-btn {
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
}

.video-content {
  position: relative;
}

.video-display {
  position: relative;
  width: 100%;
  height: 240px;
  background: #000;
}

.video-frame {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-video {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #6c757d;
}

.ai-results {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(0,0,0,0.8);
  color: white;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  max-width: 200px;
}

.detection-count {
  margin-bottom: 8px;
  font-weight: bold;
}

.alerts {
  margin-bottom: 8px;
}

.alert {
  padding: 4px 8px;
  margin-bottom: 4px;
  border-radius: 3px;
}

.alert.high {
  background: #dc3545;
}

.alert.medium {
  background: #ffc107;
  color: #000;
}

.alert.low {
  background: #17a2b8;
}

.statistics div {
  margin-bottom: 2px;
}
</style>