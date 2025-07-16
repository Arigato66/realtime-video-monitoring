import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    user: JSON.parse(localStorage.getItem('user')) || null // 修复语法错误
  }),
  
  actions: {
    async register(userData) {
      try {
        const response = await authApi.register(userData)
        return response.status === 201
      } catch (error) {
        console.error('注册失败:', error)
        return false
      }
    },
    
    async login(credentials) {
      try {
        const response = await authApi.login(credentials)
        if (response.status === 200) {
          this.token = response.data.access_token
          this.user = {
            id: response.data.user_id,
            username: credentials.username
          }
          
          localStorage.setItem('token', this.token)
          localStorage.setItem('user', JSON.stringify(this.user))
          return true
        }
        return false
      } catch (error) {
        console.error('登录失败:', error)
        return false
      }
    },
    
    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      
      // 重定向到登录页（改进：不依赖外部注入的路由）
      window.location.href = '/login'
    },
    
    // 初始化方法（改进：自动从localStorage加载状态）
    initialize() {
      const token = localStorage.getItem('token')
      const user = JSON.parse(localStorage.getItem('user'))
      
      if (token) {
        this.token = token
      }
      
      if (user) {
        this.user = user
      }
    }
  },
  
  getters: {
    isAuthenticated: (state) => !!state.token
  }
})