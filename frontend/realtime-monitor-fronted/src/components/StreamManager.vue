<template>
  <div class="stream-manager">
    <!-- 添加视频流表单 -->
    <div class="add-stream-form">
      <h3>添加新视频流</h3>
      <form @submit.prevent="addStream">
        <div class="form-group">
          <label>流名称:</label>
          <input v-model="newStream.name" type="text" required />
        </div>
        <div class="form-group">
          <label>RTMP地址:</label>
          <input v-model="newStream.rtmp_url" type="text" 
                 placeholder="rtmp://nginx-server:1935/live/stream1" required />
        </div>
        <div class="form-group">
          <label>检测模式:</label>
          <div class="checkbox-group">
            <label v-for="mode in availableModes" :key="mode.value">
              <input type="checkbox" :value="mode.value" 
                     v-model="newStream.detection_modes" />
              {{ mode.label }}
            </label>
          </div>
        </div>
        <div class="form-group">
          <label>描述:</label>
          <textarea v-model="newStream.description"></textarea>
        </div>
        <button type="submit" :disabled="isAdding">添加视频流</button>
      </form>
    </div>

    <!-- 视频流列表 -->
    <div class="stream-list">
      <h3>视频流列表</h3>
      <div class="stream-item" v-for="stream in streams" :key="stream.id">
        <div class="stream-info">
          <h4>{{ stream.name }}</h4>
          <p>状态: <span :class="stream.status">{{ stream.status }}</span></p>
          <p>RTMP: {{ stream.rtmp_url }}</p>
        </div>
        <div class="stream-actions">
          <button @click="startStream(stream.id)" 
                  :disabled="stream.status === 'active'">启动</button>
          <button @click="stopStream(stream.id)" 
                  :disabled="stream.status !== 'active'">停止</button>
          <button @click="deleteStream(stream.id)" 
                  class="danger">删除</button>
        </div>
      </div>
    </div>

    <!-- 多窗口视频显示区域 -->
    <div class="video-grid" :class="`grid-${gridSize}`">
      <div v-for="stream in activeStreams" :key="stream.id" 
           class="video-window">
        <VideoWindow :stream="stream" @close="stopStream(stream.id)" />
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue'
import { useStreamStore } from '@/stores/stream'
import VideoWindow from './VideoWindow.vue'

export default {
  name: 'StreamManager',
  components: {
    VideoWindow
  },
  setup() {
    const streamStore = useStreamStore()
    
    const newStream = reactive({
      name: '',
      rtmp_url: '',
      description: '',
      detection_modes: ['object_detection']
    })
    
    const availableModes = [
      { value: 'object_detection', label: '目标检测' },
      { value: 'face_detection', label: '人脸检测' },
      { value: 'smoking_detection', label: '吸烟检测' },
      { value: 'fall_detection', label: '跌倒检测' }
    ]
    
    const isAdding = ref(false)
    
    const streams = computed(() => streamStore.streams)
    const activeStreams = computed(() => 
      streams.value.filter(s => s.status === 'active')
    )
    const gridSize = computed(() => {
      const count = activeStreams.value.length
      if (count <= 1) return 1
      if (count <= 4) return 2
      if (count <= 9) return 3
      return 4
    })
    
    const addStream = async () => {
      isAdding.value = true
      try {
        await streamStore.addStream({ ...newStream })
        // 重置表单
        Object.assign(newStream, {
          name: '',
          rtmp_url: '',
          description: '',
          detection_modes: ['object_detection']
        })
      } catch (error) {
        console.error('添加视频流失败:', error)
      } finally {
        isAdding.value = false
      }
    }
    
    const startStream = async (streamId) => {
      await streamStore.startStream(streamId)
    }
    
    const stopStream = async (streamId) => {
      await streamStore.stopStream(streamId)
    }
    
    const deleteStream = async (streamId) => {
      if (confirm('确定要删除这个视频流吗？')) {
        await streamStore.deleteStream(streamId)
      }
    }
    
    onMounted(() => {
      streamStore.loadStreams()
    })
    
    return {
      newStream,
      availableModes,
      isAdding,
      streams,
      activeStreams,
      gridSize,
      addStream,
      startStream,
      stopStream,
      deleteStream
    }
  }
}
</script>

<style scoped>
.stream-manager {
  padding: 20px;
}

.add-stream-form {
  background: #f5f5f5;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.checkbox-group {
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: normal;
}

.stream-list {
  margin-bottom: 30px;
}

.stream-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 8px;
  margin-bottom: 10px;
}

.stream-actions {
  display: flex;
  gap: 10px;
}

.stream-actions button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.stream-actions button:not(.danger) {
  background: #007bff;
  color: white;
}

.stream-actions button.danger {
  background: #dc3545;
  color: white;
}

.stream-actions button:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.video-grid {
  display: grid;
  gap: 10px;
}

.grid-1 {
  grid-template-columns: 1fr;
}

.grid-2 {
  grid-template-columns: 1fr 1fr;
}

.grid-3 {
  grid-template-columns: repeat(3, 1fr);
}

.grid-4 {
  grid-template-columns: repeat(4, 1fr);
}

.video-window {
  border: 2px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.status.active {
  color: #28a745;
}

.status.inactive {
  color: #6c757d;
}

.status.error {
  color: #dc3545;
}
</style>