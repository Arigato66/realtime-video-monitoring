// src/api/index.js
import axios from 'axios';
import { useAuthStore } from '@/stores/auth';
import router from '@/router'; // 确保正确导入路由实例

// 创建统一的axios实例（合并基础URL配置）
const api = axios.create({
  baseURL: 'http://localhost:5000/api/v1.0', // 使用更具体的版本化URL
  timeout: 15000,
});

// 请求拦截器：统一添加Token
api.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore();
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`;
      console.log('添加 Token 到请求头:', authStore.token); // 调试用
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器：处理401错误（Token无效/过期）
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      console.log('Token 无效/过期，跳转到登录页');
      const authStore = useAuthStore();
      authStore.logout(); // 清除本地Token
      
      // 使用正确的路由跳转方式（修复router未定义问题）
      router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } });
    }
    return Promise.reject(error);
  }
);

// 认证相关API
export const authApi = {
  register(userData) {
    return api.post('/signin', userData); // 修正路径为实际后端路径
  },
  login(credentials) {
    return api.post('/login', credentials); // 修正路径为实际后端路径
  }
};

// 导出基础api实例（供其他API模块使用）
export default api;