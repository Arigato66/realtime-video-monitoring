import { io } from 'socket.io-client'
import { useStreamStore } from '@/stores/stream'

class SocketService {
    constructor() {
        this.socket = null
        this.isConnected = false
        this.reconnectAttempts = 0
        this.maxReconnectAttempts = 5
    }

    connect() {
        const serverUrl = process.env.VUE_APP_SOCKET_URL || 'http://localhost:5000'

        this.socket = io(`${serverUrl}/video`, {
            transports: ['websocket'],
            upgrade: true,
            rememberUpgrade: true,
            timeout: 20000,
            forceNew: true
        })

        this.setupEventListeners()
    }

    setupEventListeners() {
        const streamStore = useStreamStore()

        this.socket.on('connect', () => {
            console.log('WebSocket连接成功')
            this.isConnected = true
            this.reconnectAttempts = 0
        })

        this.socket.on('disconnect', () => {
            console.log('WebSocket连接断开')
            this.isConnected = false
            this.handleReconnect()
        })

        this.socket.on('connect_error', (error) => {
            console.error('WebSocket连接错误:', error)
            this.handleReconnect()
        })

        // 监听视频流数据
        this.socket.on('stream_data', (data) => {
            streamStore.updateStreamData(data)
        })

        // 监听视频流错误
        this.socket.on('stream_error', (data) => {
            streamStore.handleStreamError(data)
        })

        // 监听视频流停止
        this.socket.on('stream_stopped', (data) => {
            streamStore.handleStreamStopped(data)
        })
    }

    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++
            console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

            setTimeout(() => {
                this.connect()
            }, 2000 * this.reconnectAttempts)
        } else {
            console.error('WebSocket重连失败，已达到最大重试次数')
        }
    }

    joinStream(streamId) {
        if (this.isConnected) {
            this.socket.emit('join_stream', { stream_id: streamId })
        }
    }

    leaveStream(streamId) {
        if (this.isConnected) {
            this.socket.emit('leave_stream', { stream_id: streamId })
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect()
            this.socket = null
            this.isConnected = false
        }
    }
}

export const socketService = new SocketService()