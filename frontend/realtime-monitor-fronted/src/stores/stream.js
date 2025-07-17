import { defineStore } from 'pinia'
import { streamApi } from '@/services/streamApi'
import { socketService } from '@/services/socketService'

export const useStreamStore = defineStore('stream', {
    state: () => ({
        streams: [],
        streamData: {}, // 存储每个流的实时数据
        loading: false,
        error: null
    }),

    getters: {
        activeStreams: (state) =>
            state.streams.filter(stream => stream.status === 'active'),

        getStreamById: (state) => (id) =>
            state.streams.find(stream => stream.id === id),

        getStreamData: (state) => (streamId) =>
            state.streamData[streamId] || null
    },

    actions: {
        async loadStreams() {
            this.loading = true
            try {
                this.streams = await streamApi.getStreams()
            } catch (error) {
                this.error = error.message
                console.error('加载视频流失败:', error)
            } finally {
                this.loading = false
            }
        },

        async addStream(streamConfig) {
            try {
                const result = await streamApi.addStream(streamConfig)
                await this.loadStreams() // 重新加载列表
                return result
            } catch (error) {
                this.error = error.message
                throw error
            }
        },

        async startStream(streamId) {
            try {
                await streamApi.startStream(streamId)

                // 更新本地状态
                const stream = this.getStreamById(streamId)
                if (stream) {
                    stream.status = 'active'
                }

                // 加入WebSocket房间
                socketService.joinStream(streamId)

            } catch (error) {
                this.error = error.message
                throw error
            }
        },

        async stopStream(streamId) {
            try {
                await streamApi.stopStream(streamId)

                // 更新本地状态
                const stream = this.getStreamById(streamId)
                if (stream) {
                    stream.status = 'inactive'
                }

                // 离开WebSocket房间
                socketService.leaveStream(streamId)

                // 清除流数据
                delete this.streamData[streamId]

            } catch (error) {
                this.error = error.message
                throw error
            }
        },

        async deleteStream(streamId) {
            try {
                await streamApi.deleteStream(streamId)

                // 从本地状态中移除
                this.streams = this.streams.filter(s => s.id !== streamId)
                delete this.streamData[streamId]

            } catch (error) {
                this.error = error.message
                throw error
            }
        },

        updateStreamData(data) {
            const { stream_id, frame, ai_results, fps, timestamp } = data

            this.streamData[stream_id] = {
                frame,
                ai_results,
                fps,
                timestamp,
                lastUpdate: Date.now()
            }
        },

        handleStreamError(data) {
            const { stream_id, error } = data
            console.error(`视频流 ${stream_id} 错误:`, error)

            // 更新流状态
            const stream = this.getStreamById(stream_id)
            if (stream) {
                stream.status = 'error'
            }
        },

        handleStreamStopped(data) {
            const { stream_id } = data
            console.log(`视频流 ${stream_id} 已停止`)

            // 更新流状态
            const stream = this.getStreamById(stream_id)
            if (stream) {
                stream.status = 'inactive'
            }

            // 清除流数据
            delete this.streamData[stream_id]
        }
    }
})