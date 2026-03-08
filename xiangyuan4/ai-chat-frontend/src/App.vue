<script setup>
import { ref, onMounted } from 'vue'

const messages = ref([
  {
    id: 1,
    content: '你好！我是AI助手，有什么可以帮助你的吗？',
    sender: 'ai'
  }
])
const inputMessage = ref('')
const isLoading = ref(false)
const sessionId = ref(null) // 用于保持对话上下文的会话ID

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return
  
  const userMessage = {
    id: Date.now(),
    content: inputMessage.value.trim(),
    sender: 'user'
  }
  messages.value.push(userMessage)
  inputMessage.value = ''
  
  isLoading.value = true
  try {
    const response = await fetch('http://localhost:8000/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: userMessage.content,
        session_id: sessionId.value
      })
    })
    
    if (!response.ok) throw new Error('请求失败')
    
    const data = await response.json()
    const aiMessage = {
      id: Date.now() + 1,
      content: data.response,
      sender: 'ai'
    }
    messages.value.push(aiMessage)
    
    // 更新会话ID以保持上下文
    if (data.session_id) {
      sessionId.value = data.session_id
    }
  } catch (error) {
    console.error('错误:', error)
    const errorMessage = {
      id: Date.now() + 1,
      content: '抱歉，暂时无法响应，请稍后再试。',
      sender: 'ai'
    }
    messages.value.push(errorMessage)
  } finally {
    isLoading.value = false
  }
}

const handleKeyPress = (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

onMounted(() => {
  // 聚焦输入框
  const inputElement = document.getElementById('message-input')
  if (inputElement) {
    inputElement.focus()
  }
})
</script>

<template>
  <div class="chat-container">
    <div class="chat-header">
      <h1>AI 在线对话</h1>
    </div>
    <div class="chat-messages">
      <div 
        v-for="message in messages" 
        :key="message.id" 
        :class="['message', message.sender]"
      >
        <div class="message-content">
          {{ message.content }}
        </div>
      </div>
      <div v-if="isLoading" class="message ai loading">
        <div class="message-content">
          <div class="loading-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>
    <div class="chat-input-container">
      <textarea
        id="message-input"
        v-model="inputMessage"
        @keypress="handleKeyPress"
        placeholder="输入消息..."
        :disabled="isLoading"
      ></textarea>
      <button @click="sendMessage" :disabled="isLoading">
        发送
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat-container {
  width: 100%;
  max-width: 800px;
  height: 100vh;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  background-color: #f5f5f5;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
}

.chat-header {
  background-color: #4a6fa5;
  color: white;
  padding: 1rem;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.chat-header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.message {
  display: flex;
  max-width: 70%;
  animation: slideIn 0.3s ease-out;
}

.message.user {
  align-self: flex-end;
  justify-content: flex-end;
}

.message.ai {
  align-self: flex-start;
  justify-content: flex-start;
}

.message-content {
  padding: 0.8rem 1.2rem;
  border-radius: 18px;
  word-wrap: break-word;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.message.user .message-content {
  background-color: #4a6fa5;
  color: white;
  border-bottom-right-radius: 4px;
}

.message.ai .message-content {
  background-color: white;
  color: #333;
  border-bottom-left-radius: 4px;
}

.chat-input-container {
  display: flex;
  gap: 0.5rem;
  padding: 1rem;
  background-color: white;
  border-top: 1px solid #e0e0e0;
}

textarea {
  flex: 1;
  padding: 0.8rem;
  border: 1px solid #ddd;
  border-radius: 20px;
  resize: none;
  font-size: 1rem;
  max-height: 120px;
  font-family: inherit;
}

textarea:focus {
  outline: none;
  border-color: #4a6fa5;
}

button {
  padding: 0.8rem 1.5rem;
  background-color: #4a6fa5;
  color: white;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.2s;
  align-self: flex-end;
  min-width: 80px;
}

button:hover:not(:disabled) {
  background-color: #3a5a8c;
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.loading-dots {
  display: flex;
  gap: 0.3rem;
}

.loading-dots span {
  width: 8px;
  height: 8px;
  background-color: #666;
  border-radius: 50%;
  animation: loadingDots 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes loadingDots {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1.0);
  }
}
</style>
