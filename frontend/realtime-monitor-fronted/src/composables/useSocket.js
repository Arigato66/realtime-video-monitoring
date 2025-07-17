import { io } from 'socket.io-client'

// 简化：让代理处理路由
export function useSocket() {
  const socket = io() // 不指定 URL，使用当前域名

  return {
    socket,
    connect: () => socket.connect(),
    disconnect: () => socket.disconnect()
  }
}