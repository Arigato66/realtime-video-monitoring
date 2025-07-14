import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    user: null
  }),
  actions: {
    async register(userData) {
      try {
        const response = await authApi.register(userData)
        console.log('注册响应:', response)
        return response.status === 201
      } catch (error) {
        console.error('注册失败:', error)
        throw error
      }
    },
    async login(credentials) {
      try {
        console.log('发送登录请求:', credentials)
        const response = await authApi.login(credentials)
        console.log('收到登录响应:', response)
        console.log('响应状态:', response.status)
        console.log('响应数据:', response.data)
        
        // 检查响应状态和数据
        if (response.status === 200) {
          const responseData = response.data
          console.log('解析响应数据:', responseData)
          
          if (responseData && responseData.access_token) {
            this.token = responseData.access_token
            this.user = { user_id: responseData.user_id }
            localStorage.setItem('token', responseData.access_token)
            localStorage.setItem('user', JSON.stringify({ user_id: responseData.user_id }))
            console.log('✅ 登录成功，token已保存:', responseData.access_token)
            return true
          } else {
            console.error('❌ 响应数据中缺少access_token:', responseData)
            return false
          }
        } else {
          console.error('❌ 登录失败，状态码:', response.status)
          return false
        }
      } catch (error) {
        console.error('❌ 登录请求异常:', error)
        
        // 详细错误信息
        if (error.response) {
          console.error('服务器响应错误:', {
            status: error.response.status,
            data: error.response.data,
            headers: error.response.headers
          })
        } else if (error.request) {
          console.error('网络请求失败:', error.request)
        } else {
          console.error('请求配置错误:', error.message)
        }
        
        throw error
      }
    },
    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    }
  },
  getters: {
    isAuthenticated: (state) => !!state.token
  }
})