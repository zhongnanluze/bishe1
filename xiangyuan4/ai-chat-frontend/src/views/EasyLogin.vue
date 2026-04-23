<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authService } from '../services/authService'

const route = useRoute()
const router = useRouter()

const status = ref('准备登录...')
const isLoading = ref(true)
const error = ref('')

const autoLogin = async () => {
  const username = route.query.username || route.query.u
  
  if (!username) {
    error.value = '缺少登录参数。请使用：/easylogin?username=xxx'
    isLoading.value = false
    return
  }
  
  status.value = `正在登录用户：${username}...`
  
  try {
    const response = await authService.easyLogin(username)
    
    if (response && response.access_token) {
      localStorage.setItem('access_token', response.access_token)
      localStorage.setItem('refresh_token', response.refresh_token)
      
      status.value = '登录成功，正在跳转...'
      
      // 获取用户信息判断跳转目标
      try {
        const userInfo = await authService.getCurrentUser()
        setTimeout(() => {
          if (userInfo.is_admin) {
            router.push('/admin')
          } else {
            router.push('/chat')
          }
        }, 500)
      } catch (e) {
        setTimeout(() => {
          router.push('/chat')
        }, 500)
      }
    } else {
      error.value = '登录失败：响应中没有 token'
      isLoading.value = false
    }
  } catch (err) {
    error.value = err.message || '登录失败，请检查用户名和密码'
    isLoading.value = false
  }
}

onMounted(() => {
  autoLogin()
})
</script>

<template>
  <div class="easy-login-page">
    <div class="easy-login-card">
      <div class="logo">🚀</div>
      <h2>快捷登录</h2>
      
      <div v-if="isLoading" class="loading-state">
        <div class="spinner"></div>
        <p>{{ status }}</p>
      </div>
      
      <div v-else-if="error" class="error-state">
        <div class="error-icon">❌</div>
        <p class="error-text">{{ error }}</p>
        <router-link to="/login" class="back-link">返回正常登录</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.easy-login-page {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #020617;
}

.easy-login-card {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 48px;
  text-align: center;
  max-width: 400px;
  width: 90%;
  backdrop-filter: blur(12px);
}

.logo {
  font-size: 48px;
  margin-bottom: 16px;
}

.easy-login-card h2 {
  color: #ffffff;
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 24px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(79, 70, 229, 0.2);
  border-top-color: #4f46e5;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-state p {
  color: #94a3b8;
  font-size: 14px;
  margin: 0;
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.error-icon {
  font-size: 32px;
}

.error-text {
  color: #ef4444;
  font-size: 14px;
  margin: 0;
}

.back-link {
  color: #4f46e5;
  text-decoration: none;
  font-size: 14px;
  margin-top: 8px;
}

.back-link:hover {
  text-decoration: underline;
}
</style>
