<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'

const messages = ref([
  {
    id: 1,
    content: '你好！我是学生智能服务助手，有什么可以帮助你的吗？',
    sender: 'ai',
    agentType: 'general',
    timestamp: new Date().toLocaleTimeString()
  }
])
const inputMessage = ref('')
const isLoading = ref(false)
const sessionId = ref(null)
const currentAgent = ref('general')
const showAgentInfo = ref(false)
const useStreaming = ref(true)
const theme = ref('light') // light or dark

// 智能体信息
const agentsInfo = {
  general: {
    name: '通用助手',
    icon: '🤖',
    color: 'var(--primary-color)'
  },
  student_affairs: {
    name: '学生事务智能体',
    icon: '📋',
    color: 'var(--secondary-color)'
  },
  academic: {
    name: '学生学业智能体',
    icon: '🎓',
    color: 'var(--accent-color)'
  }
}

// 计算当前智能体信息
const currentAgentInfo = computed(() => {
  return agentsInfo[currentAgent.value] || agentsInfo.general
})

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return
  
  const userMessage = {
    id: Date.now(),
    content: inputMessage.value.trim(),
    sender: 'user',
    timestamp: new Date().toLocaleTimeString()
  }
  messages.value.push(userMessage)
  inputMessage.value = ''
  
  isLoading.value = true
  
  try {
    if (useStreaming.value) {
      await sendStreamingMessage(userMessage.content)
    } else {
      await sendNormalMessage(userMessage.content)
    }
  } catch (error) {
    console.error('错误:', error)
    const errorMessage = {
      id: Date.now() + 1,
      content: '抱歉，暂时无法响应，请稍后再试。',
      sender: 'ai',
      agentType: 'general',
      timestamp: new Date().toLocaleTimeString()
    }
    messages.value.push(errorMessage)
    scrollToBottom()
  } finally {
    isLoading.value = false
  }
}

const sendNormalMessage = async (message) => {
  const response = await fetch('http://localhost:8000/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      message: message,
      session_id: sessionId.value
    })
  })
  
  if (!response.ok) throw new Error('请求失败')
  
  const data = await response.json()
  
  if (data.session_id) {
    sessionId.value = data.session_id
  }
  if (data.agent_type) {
    currentAgent.value = data.agent_type
  }
  
  const aiMessage = {
    id: Date.now() + 1,
    content: data.response,
    sender: 'ai',
    agentType: data.agent_type || 'general',
    timestamp: new Date().toLocaleTimeString()
  }
  messages.value.push(aiMessage)
  
  scrollToBottom()
}

const sendStreamingMessage = async (message) => {
  const tempMessage = {
    id: Date.now() + 1,
    content: '',
    sender: 'ai',
    agentType: currentAgent.value,
    timestamp: new Date().toLocaleTimeString(),
    isStreaming: true
  }
  messages.value.push(tempMessage)
  scrollToBottom()
  
  const response = await fetch('http://localhost:8000/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      message: message,
      session_id: sessionId.value
    })
  })
  
  if (!response.ok) throw new Error('请求失败')
  
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  
  while (true) {
    const { done, value } = await reader.read()
    
    if (done) break
    
    buffer += decoder.decode(value, { stream: true })
    
    const lines = buffer.split('\n\n')
    buffer = lines.pop() || ''
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.substring(6))
          
          if (data.type === 'content') {
            tempMessage.content += data.content
            scrollToBottom()
          } else if (data.type === 'done') {
            tempMessage.isStreaming = false
            tempMessage.agentType = data.agent_type || 'general'
            currentAgent.value = data.agent_type || 'general'
          } else if (data.type === 'error') {
            tempMessage.content = `错误：${data.error}`
            tempMessage.isStreaming = false
          }
        } catch (e) {
          console.error('解析SSE数据错误:', e)
        }
      }
    }
  }
  
  tempMessage.isStreaming = false
}

const handleKeyPress = (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

const scrollToBottom = async () => {
  await nextTick()
  const messagesContainer = document.querySelector('.chat-messages')
  if (messagesContainer) {
    messagesContainer.scrollTop = messagesContainer.scrollHeight
  }
}

const clearMessages = () => {
  messages.value = [{
    id: Date.now(),
    content: '你好！我是学生智能服务助手，有什么可以帮助你的吗？',
    sender: 'ai',
    agentType: 'general',
    timestamp: new Date().toLocaleTimeString()
  }]
  sessionId.value = null
  currentAgent.value = 'general'
}

const toggleAgentInfo = () => {
  showAgentInfo.value = !showAgentInfo.value
}

const toggleStreaming = () => {
  useStreaming.value = !useStreaming.value
}

const toggleTheme = () => {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
  document.documentElement.setAttribute('data-theme', theme.value)
}

onMounted(() => {
  const inputElement = document.getElementById('message-input')
  if (inputElement) {
    inputElement.focus()
  }
  scrollToBottom()
  document.documentElement.setAttribute('data-theme', theme.value)
})
</script>

<template>
  <div class="app-container" :class="theme">
    <div class="chat-container">
      <!-- 聊天头部 -->
      <div class="chat-header">
        <div class="header-left">
          <div class="logo">
            <div class="logo-icon">🧠</div>
            <h1>智能服务助手</h1>
          </div>
          <div class="current-agent" @click="toggleAgentInfo">
            <span class="agent-icon">{{ currentAgentInfo.icon }}</span>
            <span class="agent-name">{{ currentAgentInfo.name }}</span>
            <span class="agent-indicator"></span>
          </div>
        </div>
        <div class="header-right">
          <button 
            class="stream-toggle" 
            @click="toggleStreaming" 
            :class="{ active: useStreaming }"
          >
            {{ useStreaming ? '⚡' : '📝' }}
          </button>
          <button class="theme-toggle" @click="toggleTheme">
            {{ theme === 'light' ? '🌙' : '☀️' }}
          </button>
          <button class="clear-btn" @click="clearMessages">
            🗑️
          </button>
        </div>
      </div>
      
      <!-- 智能体信息面板 -->
      <div v-if="showAgentInfo" class="agent-info-panel">
        <div class="agent-card">
          <div class="agent-icon">🤖</div>
          <div class="agent-details">
            <h3>通用助手</h3>
            <p>处理一般性咨询和校园生活问题</p>
          </div>
        </div>
        <div class="agent-card">
          <div class="agent-icon">📋</div>
          <div class="agent-details">
            <h3>学生事务智能体</h3>
            <p>证件补办、学费缴纳、饭卡充值、办事流程查询</p>
          </div>
        </div>
        <div class="agent-card">
          <div class="agent-icon">🎓</div>
          <div class="agent-details">
            <h3>学生学业智能体</h3>
            <p>选课、课表查询、成绩查询、GPA计算、学业日历</p>
          </div>
        </div>
      </div>
      
      <!-- 聊天消息区域 -->
      <div class="chat-messages">
        <div 
          v-for="message in messages" 
          :key="message.id" 
          :class="['message', message.sender]"
        >
          <div v-if="message.sender === 'ai'" class="message-agent-info">
            <span class="agent-badge" :style="{ backgroundColor: currentAgentInfo.color }">
              {{ currentAgentInfo.icon }} {{ currentAgentInfo.name }}
            </span>
          </div>
          <div class="message-content">
            {{ message.content }}
            <span v-if="message.isStreaming" class="streaming-cursor">|</span>
            <div class="message-timestamp">{{ message.timestamp }}</div>
          </div>
        </div>
        <div v-if="isLoading && useStreaming" class="message ai loading">
          <div class="message-agent-info">
            <span class="agent-badge" :style="{ backgroundColor: currentAgentInfo.color }">
              {{ currentAgentInfo.icon }} {{ currentAgentInfo.name }}
            </span>
          </div>
          <div class="message-content">
            <div class="loading-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 输入区域 -->
      <div class="chat-input-container">
        <textarea
          id="message-input"
          v-model="inputMessage"
          @keypress="handleKeyPress"
          placeholder="输入消息...\n\n例如：\n• 我想补办校园卡\n• 查询我的课表\n• 缴纳学费\n• 饭卡充值"
          :disabled="isLoading"
          rows="1"
        ></textarea>
        <button @click="sendMessage" :disabled="isLoading" class="send-btn">
          <span v-if="!isLoading">发送</span>
          <span v-else>发送中...</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style>
:root {
  /* 亮色主题 */
  --primary-color: #3b82f6;
  --primary-light: #93c5fd;
  --primary-dark: #2563eb;
  --secondary-color: #10b981;
  --accent-color: #8b5cf6;
  --background-color: #f8fafc;
  --surface-color: #ffffff;
  --text-primary: #1e293b;
  --text-secondary: #64748b;
  --text-muted: #94a3b8;
  --border-color: #e2e8f0;
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
  --gradient-primary: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  --gradient-secondary: linear-gradient(135deg, #10b981 0%, #059669 100%);
  --gradient-accent: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;
  --radius-2xl: 1rem;
  --radius-3xl: 1.5rem;
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
  --transition-fast: 0.15s ease;
  --transition-normal: 0.3s ease;
  --transition-slow: 0.5s ease;
}

[data-theme="dark"] {
  /* 暗色主题 */
  --primary-color: #60a5fa;
  --primary-light: #93c5fd;
  --primary-dark: #3b82f6;
  --secondary-color: #34d399;
  --accent-color: #a78bfa;
  --background-color: #0f172a;
  --surface-color: #1e293b;
  --text-primary: #f8fafc;
  --text-secondary: #cbd5e1;
  --text-muted: #94a3b8;
  --border-color: #334155;
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.2);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.3), 0 2px 4px -2px rgb(0 0 0 / 0.3);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.4), 0 4px 6px -4px rgb(0 0 0 / 0.4);
  --gradient-primary: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
  --gradient-secondary: linear-gradient(135deg, #34d399 0%, #10b981 100%);
  --gradient-accent: linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-size: 16px;
  line-height: 1.5;
  color: var(--text-primary);
  background-color: var(--background-color);
  transition: all var(--transition-normal);
}

.app-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
  background: var(--background-color);
  transition: all var(--transition-normal);
}

.chat-container {
  width: 100%;
  max-width: 800px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  background: var(--surface-color);
  border-radius: var(--radius-2xl);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  transition: all var(--transition-normal);
}

.chat-header {
  background: var(--gradient-primary);
  color: white;
  padding: var(--spacing-lg) var(--spacing-xl);
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: var(--shadow-md);
  transition: all var(--transition-normal);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-xl);
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.logo-icon {
  font-size: 1.5rem;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(10px);
}

.logo h1 {
  font-size: 1.25rem;
  font-weight: 600;
  letter-spacing: -0.025em;
}

.current-agent {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-full, 9999px);
  cursor: pointer;
  transition: all var(--transition-fast);
  backdrop-filter: blur(10px);
}

.current-agent:hover {
  background: rgba(255, 255, 255, 0.25);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.agent-icon {
  font-size: 1rem;
}

.agent-name {
  font-size: 0.875rem;
  font-weight: 500;
  white-space: nowrap;
}

.agent-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.1);
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.stream-toggle,
.theme-toggle,
.clear-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  padding: var(--spacing-sm);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-fast);
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(10px);
}

.stream-toggle:hover,
.theme-toggle:hover,
.clear-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.05);
  box-shadow: var(--shadow-md);
}

.stream-toggle.active {
  background: rgba(16, 185, 129, 0.3);
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.5);
}

.agent-info-panel {
  background: var(--surface-color);
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--spacing-md);
  animation: slideDown 0.3s ease-out;
  transition: all var(--transition-normal);
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.agent-card {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border-radius: var(--radius-xl);
  background: var(--background-color);
  border: 1px solid var(--border-color);
  transition: all var(--transition-fast);
}

.agent-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--primary-light);
}

.agent-card .agent-icon {
  font-size: 1.5rem;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-light);
  border-radius: var(--radius-lg);
  flex-shrink: 0;
}

.agent-card .agent-details h3 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--spacing-xs);
  transition: all var(--transition-normal);
}

.agent-card .agent-details p {
  font-size: 0.875rem;
  color: var(--text-secondary);
  line-height: 1.4;
  transition: all var(--transition-normal);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-xl);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
  background: var(--background-color);
  transition: all var(--transition-normal);
}

.message {
  display: flex;
  flex-direction: column;
  max-width: 75%;
  animation: slideIn 0.3s ease-out;
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

.message.user {
  align-self: flex-end;
  align-items: flex-end;
}

.message.ai {
  align-self: flex-start;
  align-items: flex-start;
}

.message-agent-info {
  margin-bottom: var(--spacing-xs);
}

.agent-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-full, 9999px);
  font-size: 0.75rem;
  font-weight: 500;
  color: white;
  background: var(--primary-color);
  backdrop-filter: blur(10px);
}

.message-content {
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--radius-xl);
  word-wrap: break-word;
  box-shadow: var(--shadow-sm);
  position: relative;
  white-space: pre-wrap;
  transition: all var(--transition-normal);
}

.message.user .message-content {
  background: var(--gradient-primary);
  color: white;
  border-bottom-right-radius: var(--radius-sm);
}

.message.ai .message-content {
  background: var(--surface-color);
  color: var(--text-primary);
  border-bottom-left-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.streaming-cursor {
  display: inline-block;
  animation: blink 1s infinite;
  margin-left: 2px;
  color: var(--primary-color);
  font-weight: bold;
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}

.message-timestamp {
  font-size: 0.75rem;
  opacity: 0.7;
  margin-top: var(--spacing-xs);
  text-align: right;
  transition: all var(--transition-normal);
}

.message.user .message-timestamp {
  color: rgba(255, 255, 255, 0.7);
}

.message.ai .message-timestamp {
  color: var(--text-muted);
}

.chat-input-container {
  display: flex;
  gap: var(--spacing-md);
  padding: var(--spacing-xl);
  background: var(--surface-color);
  border-top: 1px solid var(--border-color);
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
  transition: all var(--transition-normal);
}

textarea {
  flex: 1;
  padding: var(--spacing-md);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-xl);
  resize: none;
  font-size: 1rem;
  max-height: 120px;
  font-family: inherit;
  background: var(--background-color);
  color: var(--text-primary);
  transition: all var(--transition-fast);
  line-height: 1.4;
}

textarea:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

textarea::placeholder {
  color: var(--text-muted);
  line-height: 1.4;
}

.send-btn {
  padding: 0 var(--spacing-xl);
  background: var(--gradient-primary);
  color: white;
  border: none;
  border-radius: var(--radius-xl);
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  transition: all var(--transition-fast);
  align-self: flex-end;
  min-width: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-sm);
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.send-btn:disabled {
  background: var(--border-color);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.loading-dots {
  display: flex;
  gap: var(--spacing-xs);
  align-items: center;
  justify-content: center;
}

.loading-dots span {
  width: 8px;
  height: 8px;
  background: var(--text-muted);
  border-radius: 50%;
  animation: loadingDots 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes loadingDots {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1.0);
  }
}

/* 滚动条样式 */
.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: var(--background-color);
  border-radius: var(--radius-full, 9999px);
}

.chat-messages::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: var(--radius-full, 9999px);
  transition: all var(--transition-fast);
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .app-container {
    padding: 0;
  }
  
  .chat-container {
    max-height: 100vh;
    border-radius: 0;
  }
  
  .header-left {
    gap: var(--spacing-md);
  }
  
  .logo h1 {
    font-size: 1rem;
  }
  
  .current-agent {
    display: none;
  }
  
  .message {
    max-width: 85%;
  }
  
  .chat-messages {
    padding: var(--spacing-lg);
  }
  
  .chat-input-container {
    padding: var(--spacing-lg);
  }
  
  textarea {
    padding: var(--spacing-sm);
  }
  
  .send-btn {
    padding: 0 var(--spacing-lg);
  }
}

@media (max-height: 600px) {
  .chat-container {
    max-height: 90vh;
  }
  
  .chat-messages {
    padding: var(--spacing-md);
  }
  
  .chat-input-container {
    padding: var(--spacing-md);
  }
}
</style>