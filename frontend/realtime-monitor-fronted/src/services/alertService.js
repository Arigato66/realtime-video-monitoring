import axios from 'axios';

// 从环境变量或默认值获取API基础URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 可以添加拦截器来动态设置认证Token
apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('jwt_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, error => {
  return Promise.reject(error);
});

/**
 * 获取告警列表
 * @param {object} params - 查询参数 { page, per_page, status }
 * @returns {Promise}
 */
export const getAlerts = (params) => {
  return apiClient.get('/alerts/', { params });
};

/**
 * 更新告警状态
 * @param {number} alertId - 告警ID
 * @param {string} status - 新的状态
 * @returns {Promise}
 */
export const updateAlertStatus = (alertId, status) => {
  return apiClient.patch(`/alerts/${alertId}/status`, { status });
}; 