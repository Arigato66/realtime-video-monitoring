import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    user: JSON.parse(localStorage.getItem('user')) || null,
    router: null,
    browserOpened: false // 标记浏览器是否首次打开
  }),
  
  actions: {
    async login(credentials) {
      try {
        const response = await authApi.login(credentials)
        if (response.status === 200) {
          this.token = response.data.access_token
          this.user = {
            id: response.data.user_id,
            username: credentials.username
          }
          
          // 存储认证信息到localStorage
          localStorage.setItem('token', this.token)
          localStorage.setItem('user', JSON.stringify(this.user))
          
          // 标记浏览器已打开（用于区分刷新和完全关闭）
          sessionStorage.setItem('browserOpened', 'true')
          
          return true
        }
        return false
      } catch (error) {
        console.error('登录失败:', error)
        return false
      }
    },
    
    logout() {
      // 手动登出时清除所有存储
      this.token = null
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      sessionStorage.removeItem('browserOpened')
      
      if (this.router) {
        this.router.push('/login')
      }
    },
    
    initialize(router) {
      this.router = router
      
      // 检测浏览器是否首次打开
      const isFirstOpen = !sessionStorage.getItem('browserOpened')
      
      // 如果是首次打开（非刷新），且localStorage中有token，则保留状态
      // 如果是关闭后重新打开，则localStorage存在但sessionStorage不存在，此时应清除状态
      if (isFirstOpen && this.token) {
        this.logout() // 关闭后重新打开，清除状态
      } else {
        // 页面刷新：保留状态，更新标记
        sessionStorage.setItem('browserOpened', 'true')
      }
      
      // 监听页面关闭事件（用于多标签页场景）
      window.addEventListener('beforeunload', () => {
        // 无法可靠检测是否是最后一个标签页关闭，依赖sessionStorage自动清除特性
        // 刷新时sessionStorage保留，关闭所有标签页时sessionStorage自动清除
      })
    }
  },
  
  getters: {
    isAuthenticated: (state) => !!state.token
  }
})