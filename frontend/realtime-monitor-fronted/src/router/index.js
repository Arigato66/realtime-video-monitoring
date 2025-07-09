import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/home',
      name: 'home',
      component: () => import('../views/HomeView.vue')
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('../views/AboutView.vue')
    },
    {
      path: '/monitor',
      name: 'monitor',
      component: () => import('../views/MonitorView.vue')
    },
    // 新增登录路由
    {
      path: '/',
      name: 'login',
      component: () => import('../views/LoginView.vue')
    }
    ,
    // 新增注册路由
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue')
    },
    {
      path: '/alert',
      name: 'alert',
      component: () => import('../views/AlertView.vue')
    },
    {
    path: '/face',
    name: 'face',
    component: () => import('../views/FaceRecognition.vue')
    },
    {
    path: '/device',
    name: 'device',
    component: () => import('../views/DeviceView.vue')
    },
  ]
})

export default router