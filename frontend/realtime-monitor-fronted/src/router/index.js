import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// 先创建路由实例
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/', // 根路径重定向到登录页
      redirect: '/login'
    },
    {
      path: '/home',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
      meta: { requiresAuth: true } 
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('../views/AboutView.vue'),
      meta: { requiresAuth: true } // 需要认证
    },
    {
      path: '/face',
      name: 'face',
      component: () => import('../views/FaceView.vue'),
      meta: { requiresAuth: true } // 需要认证
    },
    {
      path: '/monitor',
      name: 'monitor',
      component: () => import('../views/MonitorView.vue'),
      meta: { requiresAuth: true } // 需要认证
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { requiresAuth: false } // 明确不需要认证
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { requiresAuth: false } // 明确不需要认证
    },
    {
      path: '/alert',
      name: 'alert',
      component: () => import('../views/AlertView.vue'),
      meta: { requiresAuth: true } // 需要认证
    },
    {
      path: '/device',
      name: 'device',
      component: () => import('../views/DeviceView.vue'),
      meta: { requiresAuth: true } // 需要认证
    }
  ]
})

// 统一的路由守卫逻辑
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  // 打印调试信息
  console.log(`导航到: ${to.path}, 需要认证: ${to.meta.requiresAuth}, 用户已认证: ${authStore.isAuthenticated}`)
  
  // 检查目标路由是否需要认证
  if (to.meta.requiresAuth) {
    // 检查用户是否已登录
    if (!authStore.isAuthenticated) {
      console.log('用户未登录，重定向到登录页')
      // 未登录，重定向到登录页
      next({
        path: '/login',
        query: { redirect: to.fullPath }
      })
    } else {
      console.log('已登录，继续访问')
      next()
    }
  } else {
    // 如果访问登录/注册页且已登录，重定向到首页
    if ((to.path === '/login' || to.path === '/register') && authStore.isAuthenticated) {
      console.log('用户已登录，重定向到首页')
      next('/home')
    } else {
      console.log('不需要认证，直接访问')
      next()
    }
  }
})

// 全局后置守卫：导航完成后执行（状态校验）
router.afterEach(() => {
  const authStore = useAuthStore();
  
  // 如果 token 无效但用户仍处于登录状态，强制登出
  if (!authStore.token && authStore.isAuthenticated) {
    authStore.logout();
  }
});


export default router