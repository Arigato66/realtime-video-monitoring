import axios from 'axios'

const API_URL = 'http://localhost:5000/api/v1.0'

export const authApi = {
  register(userData) {
    return axios.post(`${API_URL}/signin`, userData)
  },
  login(credentials) {
    return axios.post(`${API_URL}/login`, credentials)
  }
}