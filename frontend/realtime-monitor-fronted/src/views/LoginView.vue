<template>
  <!-- 动态背景容器 -->
  <div ref="login" class="login-container">
    <!-- 原有登录卡片内容 -->
    <div class="auth-card">
      <h1>登录</h1>
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label for="username">用户名</label>
          <input id="username" type="text" v-model="username" required placeholder="请输入用户名" />
        </div>
        <div class="form-group">
          <label for="password">密码</label>
          <input
            id="password"
            type="password"
            v-model="password"
            required
            placeholder="请输入密码"
          />
        </div>

        <!-- 拼图验证码（调整容器结构实现对齐） -->
        <div class="form-group captcha-group"> <!-- 复用form-group的宽度样式 -->
          <label>请拖动拼图完成验证</label>
          <button type="button" @click="onShow" class="captcha-btn">开始验证</button>
          <Vcode :show="isShow" @success="onSuccess" @close="onClose" />
        </div>

        <!-- 登录按钮 -->
        <button type="submit" :disabled="!isVerified" class="login-btn">登录</button>
      </form>

      <div class="auth-footer">
        <span>还没有账号？</span>
        <router-link to="/register" class="register-link">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
// 脚本部分保持不变
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import Vcode from "vue3-puzzle-vcode"
import * as THREE from "three"
import WAVES from "vanta/dist/vanta.waves.min"
import { useAuthStore } from '@/stores/auth'

const username = ref('admin')
const password = ref('123')
const router = useRouter()
const isShow = ref(false)
const isVerified = ref(false)
const authStore = useAuthStore()  // 创建状态管理实例
const errorMsg = ref('') 

const onShow = () => { isShow.value = true }
const onClose = () => { isShow.value = false }
const onSuccess = () => { isVerified.value = true; onClose() }

const handleLogin = async () => {
  if (!isVerified.value) {
    alert('请先完成拼图验证！')
    return
  }
  // 组装登录参数（与后端接口字段匹配）
  const credentials = {
    username: username.value,  // 如果你后端用username登录，就传这个；如果用username，改为username: username.value
    password: password.value
  }

  // 关键：打印前端即将发送的用户名和密码（开发环境调试用）
  console.log('前端登录参数：', {
    username: credentials.username,
    password: credentials.password // 注意：生产环境必须删除密码打印
  })

  try {
    // 调用Pinia中的登录方法
    const loginSuccess = await authStore.login(credentials)
    if (loginSuccess) {
      // 登录成功，跳转首页
      router.push('/home')
    } else {
      errorMsg.value = '用户名或密码错误。'
    }
  } catch (error) {
    // 处理请求异常（如网络错误、后端500错误）
    console.error('登录请求失败：', error)
    errorMsg.value = '登录失败，请检查网络或联系管理员'
  }
}

const login = ref(null)
let vantaEffect = null

onMounted(() => {
  vantaEffect = WAVES({
    el: login.value,
    THREE: THREE,
    mouseControls: true,
    touchControls: true,
    gyroControls: false,
    minHeight: 200.00,
    minWidth: 200.00,
    scale: 1.00,
    scaleMobile: 1.00,
    color: 0x0a3d62,
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
/* 基础样式保持不变 */
.login-container {
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
}

.form-group,
input {
  width: 320px;
  margin: 0 auto 1.5rem;
}

label {
  display: block;
  text-align: left;
  margin-bottom: 0.5rem;
  color: #555;
}

input {
  padding: 0.8rem;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 1rem;
}

h1 {
  margin-bottom: 2rem;
  color: #0a3d62;
}

.auth-footer {
  margin-top: 1.5rem;
}

.register-link {
  color: #1e6091;
  margin-left: 0.5rem;
  text-decoration: none;
  transition: color 0.3s;
}

.register-link:hover {
  color: #134e75;
  text-decoration: underline;
}

/* 核心修改：按钮对齐样式 */
/* 验证码按钮 - 与输入框同宽 */
.captcha-group {
  /* 继承form-group的宽度约束，确保与输入框对齐 */
  display: flex;
  flex-direction: column;
  align-items: center; /* 水平居中 */
}

.captcha-btn {
  width: 320px; /* 与输入框、登录按钮保持相同宽度 */
  background-color: #3cbbb1;
  color: white;
  border: none;
  border-radius: 5px;
  padding: 0.8rem; /* 与登录按钮相同的内边距 */
  font-size: 1rem; /* 统一字体大小 */
  cursor: pointer;
  transition: all 0.3s ease;
  margin-bottom: 1.5rem; /* 与下方登录按钮保持一致间距 */
}

.captcha-btn:hover {
  background-color: #2a9d94;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

/* 登录按钮 - 确保宽度一致 */
.login-btn {
  width: 320px; /* 关键：与验证码按钮同宽 */
  background-color: #1e6091;
  color: white;
  border: none;
  border-radius: 5px;
  padding: 0.8rem;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.login-btn:hover:not(:disabled) {
  background-color: #134e75;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.login-btn:disabled {
  background-color: #94bfe5;
  cursor: not-allowed;
}
</style>