<template>
  <div class="home-view-container">
    <Particles
      id="tsparticles"
      :particlesInit="particlesInit"
      :options="particleOptions"
    />
    <div class="content-wrapper">
      <TopBar />
      <main class="main-content">
        <div class="hero-section">
          <h1 class="title">智能监控，掌握全局</h1>
          <p class="subtitle">
            实时分析视频流，精准识别异常事件，守护每一个角落的安全。
          </p>
        </div>

        <div class="features-grid">
          <div class="feature-card" @click="navigateTo('/monitor')">
            <div class="card-icon monitor-icon">
              <Video class="w-8 h-8" />
            </div>
            <h2 class="card-title">监控大屏</h2>
            <p class="card-description">进入实时视频监控中心，查看多路视频流并进行分析。</p>
            <div class="card-link">
              进入 <ChevronRight class="w-4 h-4" />
            </div>
          </div>

          <div class="feature-card" @click="navigateTo('/alert')">
            <div class="card-icon alert-icon">
              <AlertTriangle class="w-8 h-8" />
            </div>
            <h2 class="card-title">告警中心</h2>
            <p class="card-description">处理和回顾所有安全告警，查看快照与事件回放。</p>
            <div class="card-link">
              查看 <ChevronRight class="w-4 h-4" />
            </div>
          </div>

          <div class="feature-card" @click="navigateTo('/logs')">
            <div class="card-icon logs-icon">
              <ScrollText class="w-8 h-8" />
            </div>
            <h2 class="card-title">系统日志</h2>
            <p class="card-description">浏览详细的系统操作与事件日志，用于审计与分析。</p>
            <div class="card-link">
              浏览 <ChevronRight class="w-4 h-4" />
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router';
import TopBar from '../components/TopBar.vue';
import { Video, AlertTriangle, ScrollText, ChevronRight } from 'lucide-vue-next';
import { loadFull } from 'tsparticles';

const router = useRouter();

const navigateTo = (path) => {
  router.push(path);
};

const particlesInit = async (engine) => {
  await loadFull(engine);
};

const particleOptions = {
  background: {
    color: {
      value: '#000000',
    },
  },
  fpsLimit: 120,
  interactivity: {
    events: {
      onHover: {
        enable: true,
        mode: 'repulse',
      },
      resize: true,
    },
    modes: {
      repulse: {
        distance: 100,
        duration: 0.4,
        factor: 20,
        speed: 1,
        maxSpeed: 50,
        easing: 'ease-out-quad',
      },
    },
  },
  particles: {
    color: {
      value: '#4A4A55',
    },
    links: {
      color: '#ffffff',
      distance: 150,
      enable: false,
    },
    move: {
      direction: 'none',
      enable: true,
      outModes: {
        default: 'out',
      },
      random: true,
      speed: 0.2,
      straight: false,
    },
    number: {
      density: {
        enable: true,
        area: 1200,
      },
      value: 120,
    },
    opacity: {
      value: { min: 0.3, max: 0.7 },
       animation: {
        enable: true,
        speed: 0.5,
        sync: false
      }
    },
    shape: {
      type: 'circle',
    },
    size: {
      value: { min: 1, max: 2 },
    },
  },
  detectRetina: true,
};
</script>

<style scoped>
.home-view-container {
  position: relative;
  width: 100%;
  min-height: 100vh;
  overflow: hidden;
  background-color: #000;
}

#tsparticles {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
}

.content-wrapper {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-image: radial-gradient(circle at 25% 25%, rgba(102, 126, 234, 0.15), transparent 30%),
    radial-gradient(circle at 75% 75%, rgba(118, 75, 162, 0.15), transparent 30%);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  color: #fff;
}

.hero-section {
  text-align: center;
  margin-bottom: 60px;
}

.title {
  font-size: 48px;
  font-weight: 700;
  background: linear-gradient(135deg, #a5b4fc 0%, #d8b4fe 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 16px;
  animation: slide-in-bottom 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}

.subtitle {
  font-size: 18px;
  max-width: 600px;
  margin: 0 auto;
  color: rgba(255, 255, 255, 0.7);
  animation: slide-in-bottom 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94) 0.2s both;
}

@keyframes float {
  0% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-8px);
  }
  100% {
    transform: translateY(0px);
  }
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 32px;
  width: 100%;
  max-width: 1200px;
}

.feature-card {
  position: relative;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 32px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  text-align: center;
  transition: transform 0.3s ease, background 0.3s ease;
  cursor: pointer;
  opacity: 0; /* Start hidden, animation will show it */
  animation-fill-mode: both;
}

.feature-card::before {
  content: '';
  position: absolute;
  z-index: -1;
  inset: -2px;
  border-radius: 18px;
  background: linear-gradient(135deg, #a5b4fc, #d8b4fe);
  filter: blur(20px);
  opacity: 0;
  transition: opacity 0.3s ease-in-out;
}

.features-grid .feature-card:nth-child(1) {
  animation: slide-in-bottom 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94) 0.4s both,
    float 5s ease-in-out 1.1s infinite;
}
.features-grid .feature-card:nth-child(2) {
  animation: slide-in-bottom 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94) 0.6s both,
    float 5s ease-in-out 1.8s infinite;
}
.features-grid .feature-card:nth-child(3) {
  animation: slide-in-bottom 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94) 0.8s both,
    float 5s ease-in-out 1.5s infinite;
}


.feature-card:hover {
  animation-play-state: running, paused;
  transform: translateY(-12px);
  background: rgba(255, 255, 255, 0.1);
}

.feature-card:hover::before {
  opacity: 0.4;
}

.card-icon {
  display: inline-flex;
  padding: 16px;
  border-radius: 50%;
  margin-bottom: 24px;
  color: white;
  transition: transform 0.3s ease;
}
.feature-card:hover .card-icon {
  transform: scale(1.1);
}
.monitor-icon { background: linear-gradient(135deg, #3b82f6, #1d4ed8); }
.alert-icon { background: linear-gradient(135deg, #f59e0b, #b45309); }
.logs-icon { background: linear-gradient(135deg, #10b981, #047857); }


.card-title {
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 12px;
}

.card-description {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.6;
  margin-bottom: 24px;
  min-height: 45px;
}

.card-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #a5b4fc;
  transition: color 0.3s ease;
}

.feature-card:hover .card-link {
  color: white;
}

@keyframes slide-in-bottom {
  0% {
    transform: translateY(50px);
    opacity: 0;
  }
  100% {
    transform: translateY(0);
    opacity: 1;
  }
}

@media (max-width: 992px) {
  .features-grid {
    grid-template-columns: 1fr;
    max-width: 500px;
  }
}

@media (max-width: 768px) {
  .title {
    font-size: 36px;
  }
  .subtitle {
    font-size: 16px;
  }
}
</style>