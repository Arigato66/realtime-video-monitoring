import axios from 'axios'

// 简化：直接使用相对路径
const API_URL = '/api/v1.0'

export const authApi = {
  register: (userData) => {
    return axios.post(`${API_URL}/signin`, userData)
  },
  login: (credentials) => {
    return axios.post(`${API_URL}/login`, credentials)
  }
}