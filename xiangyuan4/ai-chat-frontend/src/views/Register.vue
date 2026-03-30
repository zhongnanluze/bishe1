<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { authService } from '../services/authService'
import LineWaves from './vueBits/LineWaves.vue'

const router = useRouter()
const isLoading = ref(false)
const error = ref('')

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  student_id: '',
  full_name: ''
})

const handleRegister = async () => {
  if (!registerForm.username || !registerForm.email || !registerForm.password) {
    error.value = '请填写所有必填字段'
    return
  }

  // 简单的邮箱验证
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(registerForm.email)) {
    error.value = '请输入有效的邮箱地址'
    return
  }

  // 密码长度验证
  if (registerForm.password.length < 6) {
    error.value = '密码长度至少为6位'
    return
  }
  
  // 密码长度上限验证（后端限制72字节）
  if (registerForm.password.length > 72) {
    error.value = '密码长度不能超过72位'
    return
  }

  isLoading.value = true
  error.value = ''

  try {
    const response = await authService.register(registerForm)
    
    if (response && response.success) {
      // 注册成功，跳转到登录页面
      router.push('/login')
    } else {
      error.value = '注册失败，请检查响应数据'
    }
  } catch (err) {
    error.value = err.message || '注册失败，请稍后重试'
  } finally {
    isLoading.value = false
  }
}

const goToLogin = () => {
  router.push('/login')
}
</script>

<template>
  <div style="width: 100%; height: 100vh; position: relative; background-color: #000000;">
    <LineWaves
      style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 0;"
      :speed="0.3"
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
      :mouseInfluence="2"
    />
    <div class="auth-container">
      <div class="auth-card">
        <div class="auth-header">
          <div class="logo">
            <div class="logo-icon">🧠</div>
            <h1>智能服务助手</h1>
          </div>
          <h2>用户注册</h2>
          <p>创建新账号</p>
        </div>

        <div class="auth-form">
          <div v-if="error" class="error-message">
            {{ error }}
          </div>

          <div class="form-group">
            <label for="username">用户名 <span class="required">*</span></label>
            <input
              type="text"
              id="username"
              v-model="registerForm.username"
              placeholder="请输入用户名"
              :disabled="isLoading"
            />
          </div>

          <div class="form-group">
            <label for="email">邮箱 <span class="required">*</span></label>
            <input
              type="email"
              id="email"
              v-model="registerForm.email"
              placeholder="请输入邮箱"
              :disabled="isLoading"
            />
          </div>

          <div class="form-group">
            <label for="password">密码 <span class="required">*</span></label>
            <input
              type="password"
              id="password"
              v-model="registerForm.password"
              placeholder="请输入密码（6-72位）"
              :disabled="isLoading"
            />
          </div>

          <div class="form-group">
            <label for="student_id">学号</label>
            <input
              type="text"
              id="student_id"
              v-model="registerForm.student_id"
              placeholder="请输入学号（可选）"
              :disabled="isLoading"
            />
          </div>

          <div class="form-group">
            <label for="full_name">真实姓名</label>
            <input
              type="text"
              id="full_name"
              v-model="registerForm.full_name"
              placeholder="请输入真实姓名（可选）"
              :disabled="isLoading"
            />
          </div>

          <button
            class="auth-button"
            @click="handleRegister"
            :disabled="isLoading"
          >
            <span v-if="!isLoading">注册</span>
            <span v-else>注册中...</span>
          </button>

          <div class="auth-footer">
            <p>已有账号？ <a href="#" @click.prevent="goToLogin">立即登录</a></p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
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

.required {
  color: #dc2626;
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