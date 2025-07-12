<template>
  <!-- 动态背景容器（与登录页一致） -->
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
          >
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
          >
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
          >
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
          >
        </div>
        <button type="submit" class="submit-btn">注册</button>
      </form>
      
      <div class="auth-footer">
        <span>已有账号？</span>
        <router-link to="/login" class="login-link">立即登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import * as THREE from "three"
import WAVES from "vanta/dist/vanta.waves.min"

// 注册表单数据
const name = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const router = useRouter()

// 注册处理逻辑
const handleRegister = () => {
  if (password.value !== confirmPassword.value) {
    alert('两次输入的密码不一致')
    return
  }
  
  console.log('注册信息:', { 
    name: name.value,
    email: email.value,
    password: password.value
  })
  
  router.push('/')
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
    color: 0x0a3d62, // 与登录页相同的波浪蓝色
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
/* 基础容器样式 */
.auth-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  overflow: hidden;
}

/* 注册卡片样式 */
.auth-card {
  background: rgba(255, 255, 255, 0.92);
  padding: 2.5rem;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  width: 400px;
  text-align: center;
  position: relative;
  z-index: 10; /* 确保在背景上方 */
  transition: transform 0.3s ease;
}

/* 标题样式 */
h1 {
  margin-bottom: 2rem;
  color: #0a3d62; /* 与波浪背景同色 */
  font-size: 26px;
  position: relative;
  animation: fadeIn 0.8s ease;
}

/* 表单组样式 */
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

/* 输入框动态效果 */
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
  border-color: #3cbbb1; /* 聚焦时使用蓝绿色边框 */
  box-shadow: 0 0 0 3px rgba(60, 187, 177, 0.2);
  transform: translateY(-2px);
}

/* 注册按钮样式（与登录页匹配） */
.submit-btn {
  width: 320px;
  background-color: #1e6091; /* 与登录按钮同色 */
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

.submit-btn:hover {
  background-color: #134e75;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

/* 底部链接样式 */
.auth-footer {
  margin-top: 1.5rem;
}

.login-link {
  color: #1e6091; /* 与按钮同色 */
  margin-left: 0.5rem;
  text-decoration: none;
  transition: color 0.3s ease;
  position: relative;
}

.login-link:hover {
  color: #134e75;
  text-decoration: none;
}

.login-link::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 0;
  height: 2px;
  background-color: #1e6091;
  transition: width 0.3s ease;
}

.login-link:hover::after {
  width: 100%;
}

/* 动画效果 */
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

/* 响应式调整 */
@media (max-width: 480px) {
  .auth-card {
    width: 90%;
    padding: 1.5rem;
  }
  
  .form-group,
  .form-input,
  .submit-btn {
    width: 100%;
  }
}
</style>