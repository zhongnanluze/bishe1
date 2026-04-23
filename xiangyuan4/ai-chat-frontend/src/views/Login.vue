<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { authService } from '../services/authService'
import LineWaves from './vueBits/LineWaves.vue'
const router = useRouter()
const isLoading = ref(false)
const error = ref('')

 const loginForm = reactive({
username: '',
password: ''
})

// 登录处理
const handleLogin = async () => {
  console.log('=== 登录开始 ===')
  console.log('用户名:', loginForm.username)
  console.log('密码长度:', loginForm.password.length)

  if (!loginForm.username || !loginForm.password) {
    error.value = '请填写所有必填字段'
    console.log('错误: 字段为空')
    return
  }

  // 密码长度验证（后端限制72字节）
  const passwordBytes = new Blob([loginForm.password]).size
  if (passwordBytes > 72) {
    error.value = '密码长度不能超过72字节'
    console.log('错误: 密码过长')
    return
  }

  isLoading.value = true
  error.value = ''
  console.log('开始调用登录接口...')

  try {
    const response = await authService.login(loginForm.username, loginForm.password)
    console.log('登录响应:', response)

    if (response && response.access_token) {
      // 登录成功，保存token
      localStorage.setItem('access_token', response.access_token)
      localStorage.setItem('refresh_token', response.refresh_token)
      
      // 获取用户信息，判断是否是管理员
      try {
        const userInfo = await authService.getCurrentUser()
        console.log('用户信息:', userInfo)
        
        if (userInfo.is_admin) {
          console.log('管理员登录，跳转到管理后台')
          router.push('/admin')
        } else {
          console.log('普通用户登录，跳转到聊天页面')
          router.push('/chat')
        }
      } catch (userInfoError) {
        console.error('获取用户信息失败:', userInfoError)
        // 获取用户信息失败时，默认跳转到聊天页面
        console.log('获取用户信息失败，默认跳转到聊天页面')
        router.push('/chat')
      }
    } else {
      error.value = '登录失败，请检查响应数据'
      console.log('错误: 响应中没有access_token')
    }
  } catch (err) {
    console.error('登录错误:', err)
    error.value = err.message || '登录失败，请检查用户名和密码'
  } finally {
    isLoading.value = false
    console.log('=== 登录结束 ===')
  }
}

// 注册跳转
const goToRegister = () => {
  router.push('/register')
}

// 输入时清空错误
const clearError = () => {
  if (error.value) error.value = ''
}
</script>


<template>
  <div style="width: 100%; height: 100vh; position: relative; background-color: #000000;">
    <LineWaves
      style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 0;"
      :speed="0.1"
      :innerLineCount="32"
      :outerLineCount="36"
      :warpIntensity="1"
      :rotation="-45"
      :edgeFadeWidth="0"
      :colorCycleSpeed="1"
      :brightness="0.5"
      :color1="'#3b82f6'"
      :color2="'#8b5cf6'"
      :color3="'#ec4899'"
      :enableMouseInteraction="true"
      :mouseInfluence="3"
    />
    <div class="auth-container">
      <div class="auth-card">
        <div class="auth-header">
<!--          <div class="logo">-->
<!--            <div class="logo-icon">🧠</div>-->
<!--            <h1>智能服务助手</h1>-->
<!--          </div>-->
          <h2>用户登录</h2>
          <p>请输入您的账号和密码</p>
        </div>

        <div class="auth-form">
          <div v-if="error" class="error-message">
            {{ error }}
          </div>

          <div class="form-group">
            <label for="username">用户名/邮箱</label>
            <input
              type="text"
              id="username"
              v-model="loginForm.username"
              placeholder="请输入用户名或邮箱"
              :disabled="isLoading"
              @input="clearError"
              @keyup.enter="handleLogin"
            />
          </div>

          <div class="form-group">
            <label for="password">密码</label>
            <input
              type="password"
              id="password"
              v-model="loginForm.password"
              placeholder="请输入密码"
              :disabled="isLoading"
              @input="clearError"
              @keyup.enter="handleLogin"
            />
          </div>

          <button
            class="auth-button"
            @click="handleLogin"
            :disabled="isLoading"
          >
            <span v-if="!isLoading">登录</span>
            <span v-else>登录中...</span>
          </button>

          <div class="auth-footer">
            <p>还没有账号？ <a href="#" @click.prevent="goToRegister">立即注册</a></p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
/* 加在 <style> 最顶部 */
.auth-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  z-index: 1;
  background-color: transparent;
}



.auth-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 1rem;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
  width: 70%;
  max-width: 700px;
  overflow: hidden;
}

.auth-header {
  background: rgba(59, 130, 246, 0.8);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  padding: 2.5rem;
  text-align: center;
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.logo-icon {
  font-size: 2rem;
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  backdrop-filter: blur(10px);
}

.logo h1 {
  font-size: 1.8rem;
  font-weight: 600;
  margin: 0;
}

.auth-header h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.4rem;
  font-weight: 500;
}

.auth-header p {
  margin: 0;
  opacity: 0.9;
  font-size: 1rem;
}

.auth-form {
  padding: 3rem 4rem; /* 内边距更舒服 */
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
}

.error-message {
  background: #fee2e2;
  color: #dc2626;
  padding: 0.75rem;
  border-radius: 0.5rem;
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
  text-align: center;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
  font-size: 1rem;
}

/* 输入框100%拉满 */
.form-group input {
  width: 100%;
  padding: 1rem 1.2rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 0.5rem;
  font-size: 1.1rem;
  transition: all 0.2s ease;
  box-sizing: border-box;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.9);
}

.form-group input::placeholder {
  color: rgba(255, 255, 255, 0.6);
}

.form-group input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3);
  background: rgba(255, 255, 255, 0.15);
}

.form-group input:disabled {
  background: rgba(255, 255, 255, 0.05);
  cursor: not-allowed;
  border-color: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.5);
}

/* 按钮100%拉满 */
.auth-button {
  width: 100%;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border: none;
  padding: 1.1rem;
  border-radius: 0.5rem;
  font-size: 1.1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 1.5rem;
}

.auth-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.auth-button:disabled {
  background: #d1d5db;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.auth-footer {
  text-align: center;
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.7);
}

.auth-footer a {
  color: #3b82f6;
  text-decoration: none;
  font-weight: 500;
}

.auth-footer a:hover {
  text-decoration: underline;
  color: #60a5fa;
}

/* 移动端自适应 */
@media (max-width: 768px) {
  .auth-card {
    max-width: 700px;
  }
  .auth-form {
    padding: 2rem;
  }
}
</style>

