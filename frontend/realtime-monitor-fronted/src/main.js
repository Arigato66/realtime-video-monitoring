import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { useAuthStore } from './stores/auth'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// 初始化认证状态
const authStore = useAuthStore()
authStore.initialize(router)


app.mount('#app') 