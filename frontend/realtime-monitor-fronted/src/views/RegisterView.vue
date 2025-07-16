<template>
  <!-- 动态背景容器 -->
  <div ref="register" class="auth-container">
    <div class="auth-card">
      <h1>注册</h1>
      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label for="name">用户名</label>
          <input 
            id="name" 
            type="text" 
            v-model="name" 
            required
            placeholder="请输入用户名"
            class="form-input"
            :class="{ 'error-input': errors.name }"
          >
          <p class="error-message">{{ errors.name }}</p>
        </div>
        
        <div class="form-group">
          <label for="email">邮箱</label>
          <input 
            id="email" 
            type="email" 
            v-model="email" 
            required
            placeholder="请输入邮箱"
            class="form-input"
            :class="{ 'error-input': errors.email }"
          >
          <p class="error-message">{{ errors.email }}</p>
        </div>
        
        <div class="form-group">
          <label for="password">密码</label>
          <input
            id="password"
            type="password"
            v-model="password"
            required
            placeholder="请输入密码"
            class="form-input"
            :class="{ 'error-input': errors.password }"
          >
          <p class="error-message">{{ errors.password }}</p>
        </div>
        
        <div class="form-group">
          <label for="confirmPassword">确认密码</label>
          <input
            id="confirmPassword"
            type="password"
            v-model="confirmPassword"
            required
            placeholder="请再次输入密码"
            class="form-input"
            :class="{ 'error-input': errors.confirmPassword }"
          >
          <p class="error-message">{{ errors.confirmPassword }}</p>
        </div>
        
        <!-- 拼图验证码（与登录页保持一致） -->
        <div class="form-group captcha-group">
          <label>请拖动拼图完成验证</label>
          <button type="button" @click="onShow" class="captcha-btn">开始验证</button>
          <Vcode :show="isShow" @success="onSuccess" @close="onClose" />
        </div>
        
        <button 
          type="submit" 
          class="submit-btn"
          :disabled="isLoading || !isVerified"
        >
          <span v-if="!isLoading">注册</span>
          <span v-if="isLoading">注册中...</span>
        </button>
        
        <!-- 全局错误提示 -->
        <p class="global-error" v-if="globalError">{{ globalError }}</p>
        <!-- 成功提示 -->
        <p class="success-message" v-if="successMessage">{{ successMessage }}</p>
      </form>
      
      <div class="auth-footer">
        <span>已有账号？</span>
        <router-link to="/" class="login-link">立即登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import * as THREE from "three"
import WAVES from "vanta/dist/vanta.waves.min"
import Vcode from "vue3-puzzle-vcode"  // 引入验证码组件（与登录页一致）
import { useAuthStore } from '@/stores/auth'  // 引入Pinia状态管理（与登录页一致）

// 表单数据
const name = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')

// 状态管理（与登录页保持一致的验证逻辑）
const isLoading = ref(false)
const isShow = ref(false)  // 验证码显示状态
const isVerified = ref(false)  // 验证通过状态
const errors = ref({
  name: '',
  email: '',
  password: '',
  confirmPassword: ''
})
const globalError = ref('')
const successMessage = ref('')

const router = useRouter()
const authStore = useAuthStore()  // 创建状态管理实例

// 验证码控制方法（与登录页一致）
const onShow = () => { isShow.value = true }
const onClose = () => { isShow.value = false }
const onSuccess = () => { isVerified.value = true; onClose() }

// 表单验证
const validateForm = () => {
  let isValid = true
  errors.value = {}  // 重置错误信息
  
  // 用户名验证
  if (!name.value.trim()) {
    errors.value.name = '请输入用户名'
    isValid = false
  } else if (name.value.length < 3) {
    errors.value.name = '用户名至少需要3个字符'
    isValid = false
  }
  
  // 邮箱验证
  if (!email.value.trim()) {
    errors.value.email = '请输入邮箱'
    isValid = false
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
    errors.value.email = '请输入有效的邮箱地址'
    isValid = false
  }
  
  // 密码验证
  if (!password.value) {
    errors.value.password = '请输入密码'
    isValid = false
  } else if (password.value.length < 6) {
    errors.value.password = '密码至少需要6个字符'
    isValid = false
  }
  
  // 确认密码验证
  if (!confirmPassword.value) {
    errors.value.confirmPassword = '请确认密码'
    isValid = false
  } else if (password.value !== confirmPassword.value) {
    errors.value.confirmPassword = '两次输入的密码不一致'
    isValid = false
  }
  
  return isValid
}

// 注册处理逻辑（与登录页的Pinia调用方式一致）
const handleRegister = async () => {
  // 验证逻辑：先完成验证码（与登录页一致）
  if (!isVerified.value) {
    globalError.value = '请先完成拼图验证！'
    return
  }
  
  // 清除之前的提示信息
  globalError.value = ''
  successMessage.value = ''
  
  // 前端表单验证
  if (!validateForm()) {
    return
  }
  
  try {
    isLoading.value = true  // 显示加载状态
    
    // 组装注册参数（与后端接口字段匹配）
    const userData = {
      username: name.value,  // 与后端RegisterService的参数一致
      email: email.value,
      password: password.value
    }
    
    // 调用Pinia中的注册方法（与登录页的状态管理方式一致）
    const registerSuccess = await authStore.register(userData)
    
    if (registerSuccess) {
      // 注册成功处理
      successMessage.value = '注册成功，即将跳转到登录页...'
      console.log('注册成功:', registerSuccess)
      
      // 2秒后跳转到登录页（与登录页的路由跳转逻辑一致）
      setTimeout(() => {
        router.push('/')
      }, 2000)
    } else {
      globalError.value = '注册失败，请检查信息后重试'
    }
    
  } catch (error) {
    // 错误处理（详细打印错误信息）
    console.error('注册请求失败:', error)
    
    if (error.response) {
      // 后端返回的错误信息（与登录页的错误处理逻辑一致）
      globalError.value = error.response.data.error || '服务器错误'
    } else if (error.request) {
      // 网络错误（无响应）
      globalError.value = '无法连接到服务器，请检查后端是否运行'
    } else {
      // 请求配置错误
      globalError.value = `请求错误: ${error.message}`
    }
  } finally {
    isLoading.value = false  // 确保加载状态关闭
  }
}

// 动态背景效果（与登录页保持一致）
const register = ref(null)
let vantaEffect = null

onMounted(() => {
  vantaEffect = WAVES({
    el: register.value,
    THREE: THREE,
    mouseControls: true,
    touchControls: true,
    gyroControls: false,
    minHeight: 200.00,
    minWidth: 200.00,
    scale: 1.00,
    scaleMobile: 1.00,
    color: 0x0a3d62,  // 与登录页背景色一致
    shininess: 30,
    waveHeight: 20,
    waveSpeed: 1.5
  })
})

onUnmounted(() => {
  if (vantaEffect) vantaEffect.destroy()
})
</script>

<style scoped>
/* 基础样式保持不变，新增验证码相关样式（与登录页一致） */
.auth-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  overflow: hidden;
}

.auth-card {
  background: rgba(255, 255, 255, 0.92);
  padding: 2.5rem;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  width: 400px;
  text-align: center;
  position: relative;
  z-index: 10;
  transition: transform 0.3s ease;
}

/* 验证码样式（与登录页保持一致，确保UI统一） */
.captcha-group {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.captcha-btn {
  width: 320px;  /* 与输入框、注册按钮同宽 */
  background-color: #3cbbb1;
  color: white;
  border: none;
  border-radius: 5px;
  padding: 0.8rem;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-bottom: 1.5rem;
}

.captcha-btn:hover {
  background-color: #2a9d94;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

/* 其他样式保持不变 */
h1 {
  margin-bottom: 2rem;
  color: #0a3d62;
  font-size: 26px;
  animation: fadeIn 0.8s ease;
}

.form-group {
  width: 320px;
  margin: 0 auto 1.5rem;
}

label {
  display: block;
  text-align: left;
  margin-bottom: 0.5rem;
  color: #555;
  font-size: 14px;
}

.form-input {
  width: 100%;
  padding: 0.8rem;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 1rem;
  transition: all 0.3s ease;
}

.form-input:focus {
  outline: none;
  border-color: #3cbbb1;
  box-shadow: 0 0 0 3px rgba(60, 187, 177, 0.2);
  transform: translateY(-2px);
}

.submit-btn {
  width: 320px;
  background-color: #1e6091;
  color: white;
  border: none;
  border-radius: 5px;
  padding: 0.8rem;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
  margin: 0 auto 1.5rem;
  display: block;
}

.submit-btn:hover:not(:disabled) {
  background-color: #134e75;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.submit-btn:disabled {
  background-color: #94b3c7;
  cursor: not-allowed;
}

.error-input {
  border-color: #e53e3e !important;
}

.error-message {
  color: #e53e3e;
  font-size: 0.875rem;
  margin: 0.25rem 0 0 0;
  text-align: left;
  min-height: 1.2rem;
}

.global-error {
  color: #e53e3e;
  margin: 0 0 1rem 0;
}

.success-message {
  color: #22c55e;
  margin: 0 0 1rem 0;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 480px) {
  .auth-card {
    width: 90%;
    padding: 1.5rem;
  }
  
  .form-group,
  .form-input,
  .submit-btn,
  .captcha-btn {
    width: 100%;
  }
}
</style>