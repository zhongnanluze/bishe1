<script setup>
import { ref } from 'vue'
import { authService } from '../services/authService'
import { useRouter } from 'vue-router'

const router = useRouter()
const message = ref('')

const clearLocalStorage = () => {
  localStorage.clear()
  message.value = '本地存储已清除！'
  console.log('本地存储已清除')
}

const checkAuthStatus = () => {
  const isLoggedIn = authService.isLoggedIn()
  const accessToken = localStorage.getItem('access_token')
  const refreshToken = localStorage.getItem('refresh_token')
  
  message.value = `
    登录状态: ${isLoggedIn}
    Access Token: ${accessToken ? '存在' : '不存在'}
    Refresh Token: ${refreshToken ? '存在' : '不存在'}
  `
  console.log('登录状态:', isLoggedIn)
  console.log('Access Token:', accessToken)
  console.log('Refresh Token:', refreshToken)
}

const goToLogin = () => {
  router.push('/login')
}

const goToChat = () => {
  router.push('/chat')
}
</script>

<template>
  <div class="debug-container">
    <h1>调试页面</h1>
    <div class="debug-actions">
      <button @click="clearLocalStorage" class="debug-btn">
        清除本地存储
      </button>
      <button @click="checkAuthStatus" class="debug-btn">
        检查登录状态
      </button>
      <button @click="goToLogin" class="debug-btn">
        跳转到登录页面
      </button>
      <button @click="goToChat" class="debug-btn">
        跳转到聊天页面
      </button>
    </div>
    <div v-if="message" class="debug-message">
      {{ message }}
    </div>
  </div>
</template>

<style scoped>
.debug-container {
  max-width: 800px;
  margin: 2rem auto;
  padding: 2rem;
  background: white;
  border-radius: 1rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.debug-container h1 {
  margin-bottom: 1.5rem;
  color: #1e293b;
}

.debug-actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.debug-btn {
  padding: 0.75rem 1.5rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  transition: all 0.2s ease;
}

.debug-btn:hover {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.debug-message {
  padding: 1rem;
  background: #f1f5f9;
  border-radius: 0.5rem;
  white-space: pre-wrap;
  color: #334155;
  font-family: monospace;
}
</style>