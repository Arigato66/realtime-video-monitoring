import axios from 'axios'

const API_BASE_URL = process.env.VUE_APP_API_URL || '/api'

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json'
    }
})

// 请求拦截器
api.interceptors.request.use(
    config => {
        const token = localStorage.getItem('access_token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    error => Promise.reject(error)
)

// 响应拦截器
api.interceptors.response.use(
    response => response,
    error => {
        if (error.response?.status === 401) {
            // 处理认证失败
            localStorage.removeItem('access_token')
            window.location.href = '/login'
        }
        return Promise.reject(error)
    }
)

export const streamApi = {
    // 获取所有视频流
    async getStreams() {
        const response = await api.get('/api/streams')
        return response.data
    },

    // 添加新视频流
    async addStream(streamConfig) {
        const response = await api.post('/api/streams', streamConfig)
        return response.data
    },

    // 启动视频流
    async startStream(streamId) {
        const response = await api.post(`/api/streams/${streamId}/start`)
        return response.data
    },

    // 停止视频流
    async stopStream(streamId) {
        const response = await api.post(`/api/streams/${streamId}/stop`)
        return response.data
    },

    // 删除视频流
    async deleteStream(streamId) {
        const response = await api.delete(`/api/streams/${streamId}`)
        return response.data
    },

    // 获取视频流状态
    async getStreamStatus(streamId) {
        const response = await api.get(`/api/streams/${streamId}/status`)
        return response.data
    }
}