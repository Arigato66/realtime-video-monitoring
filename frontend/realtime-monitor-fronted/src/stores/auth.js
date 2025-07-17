import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
       user: (() => {
      try {
        const userStr = localStorage.getItem('user')
        // 只有非空字符串才尝试解析
        return userStr ? JSON.parse(userStr) : null
      } catch (e) {
        console.error('解析本地用户数据失败:', e)
        // 解析失败时清除错误数据
        localStorage.removeItem('user')
        return null
      }
    })(),
    router: null,
  }),
  
  actions: {
    // 新增：注册方法
    async register(userData) {
      try {
        const response = await authApi.register(userData) // 调用注册API
        if (response.status === 200 || response.status === 201) { // 注册成功状态码通常是201
          // 注册成功后可自动登录，或返回成功状态让用户手动登录
          return {
            success: true,
            message: '注册成功'
          }
        }
        return {
          success: false,
          message: '注册失败，服务器返回非成功状态'
        }
      } catch (error) {
        console.error('注册失败:', error)
        return {
          success: false,
          message: error.message || '注册过程发生错误'
        }
      }
    },

  async login(credentials) {
  try {
    console.log("发送登录请求：", credentials);
    const response = await authApi.login(credentials);
    
    console.log("登录成功，响应数据：", response.data);
    this.token = response.data.access_token;
    this.user = {
      id: response.data.user_id,
      username: credentials.username
    };
    
    localStorage.setItem('token', this.token);
    localStorage.setItem('user', JSON.stringify(this.user));
    sessionStorage.setItem('browserOpened', 'true');
    
    // 确保在路由跳转前状态已更新
    if (this.router) {
      // 使用 replace 而不是 push 防止回退到登录页
      this.router.replace('/home');
    }
    
    return { success: true, message: "登录成功" };
    
  } catch (error) {
    console.error("登录失败详情：", error);
    
    // 特殊处理超时错误
    let errorMsg = "登录失败，请重试";
    if (error.code === 'ECONNABORTED') {
      errorMsg = "连接超时，请检查网络连接";
    } else if (error.response) {
      errorMsg = error.response.data?.error || errorMsg;
    }
    
    // 清除无效的认证信息
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    this.token = null;
    this.user = null;
    
    return { success: false, message: errorMsg };
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
      
      // 如果是首次打开（非刷新），且localStorage中有token，则清除状态（避免关闭后重新打开仍保留登录状态）
      if (isFirstOpen && this.token) {
        this.logout()
      } else {
        // 页面刷新：保留状态，更新标记
        sessionStorage.setItem('browserOpened', 'true')
      }
    }
  },
  
  getters: {
    isAuthenticated: (state) => !!state.token
  }
})