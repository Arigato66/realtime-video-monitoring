import axios from 'axios'

// 使用环境变量
const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1.0'

export const authApi = {
  register(userData) {
    return axios.post(`${API_URL}/signin`, userData)
  },
  login(credentials) {
    return axios.post(`${API_URL}/login`, credentials)
  }
}
