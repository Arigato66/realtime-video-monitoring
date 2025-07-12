import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null
  }),
  actions: {
    async register(userData) {
      const response = await authApi.register(userData)
      if (response.status === 201) {
        return true
      }
    },
    async login(credentials) {
      const response = await authApi.login(credentials)
      if (response.status === 200) {
        this.token = response.data.access_token
        localStorage.setItem('token', this.token)
        return true
      }
      return false
    },
    logout() {
      this.token = null
      localStorage.removeItem('token')
    }
  },
  getters: {
    isAuthenticated: (state) => !!state.token
  }
})