<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { apiService } from '../services/apiService'
import { authService } from '../services/authService'
import { marked } from 'marked'

const messages = ref([
  {
    id: 1,
    content: '你好！我是学生智能服务助手，有什么可以帮助你的吗？',
    sender: 'ai',
    agentType: 'chat',
    timestamp: new Date().toLocaleTimeString()
  }
])
const inputMessage = ref('')
const isLoading = ref(false)
const sessionId = ref(null)
const currentAgent = ref('chat')
const showAgentInfo = ref(false)
const theme = ref('dark') // 固定为深色主题
const userInfo = ref(null)
const router = useRouter()
const showSessions = ref(true) // 默认显示会话列表
const sessions = ref([])
const isLoadingSessions = ref(false)
const currentSessionName = ref('新对话')
const currentSessionCreatedAt = ref(null)
const showMenu = ref(false) // 控制菜单显示
const showEditProfile = ref(false) // 控制修改个人信息弹窗显示
const editProfileForm = ref({ // 修改个人信息表单
  username: '',
  email: '',
  fullName: '',
  studentId: '',
  avatar: '',
  jwxtUsername: '',
  jwxtPassword: ''
})
const isUpdatingProfile = ref(false) // 控制更新状态
const showChangePassword = ref(false) // 控制修改密码弹窗显示
const changePasswordForm = ref({ // 修改密码表单
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})
const isChangingPassword = ref(false) // 控制修改密码状态
const selectedSessionId = ref(null) // 跟踪当前选中的会话ID

const agentsInfo = {
  chat: {
    name: '日常聊天智能体',
    icon: '💬',
    color: 'var(--primary-color)'
  },
  academic: {
    name: '学生学业智能体',
    icon: '🎓',
    color: 'var(--accent-color)'
  },
  student_services: {
    name: '学生办事智能体',
    icon: '📋',
    color: 'var(--secondary-color)'
  },
  psychology: {
    name: '心理咨询智能体',
    icon: '🧡',
    color: '#f472b6'
  },
  policy: {
    name: '制度查询智能体',
    icon: '📜',
    color: '#fbbf24'
  }
}

const currentAgentInfo = computed(() => {
  return agentsInfo[currentAgent.value] || agentsInfo.chat
})

// 解析Markdown内容
const parseMarkdown = (content) => {
  return marked(content)
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return
  
  const userMessage = {
    id: Date.now(),
    content: inputMessage.value.trim(),
    sender: 'user',
    timestamp: new Date().toLocaleTimeString()
  }
  messages.value.push(userMessage)
  scrollToBottom()
  inputMessage.value = ''
  
  isLoading.value = true
  
  try {
    // 如果还没有会话ID，创建一个新会话
    if (!sessionId.value) {
      const response = await apiService.post('/session', { user_info: userInfo.value })
      sessionId.value = response.session_id
      selectedSessionId.value = response.session_id
    }
    
    await sendStreamingMessage(userMessage.content)
  } catch (error) {
    console.error('错误:', error)
    const errorMessage = {
      id: Date.now() + 1,
      content: '抱歉，暂时无法响应，请稍后再试。',
      sender: 'ai',
      agentType: 'chat',
      timestamp: new Date().toLocaleTimeString()
    }
    messages.value.push(errorMessage)
    scrollToBottom()
  } finally {
    isLoading.value = false
  }
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
  
  const body = await apiService.stream('/chat/stream', {
    message: message,
    session_id: sessionId.value
  })
  
  const reader = body.getReader()
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
            tempMessage.agentType = data.agent_type || 'chat'
            currentAgent.value = data.agent_type || 'chat'
            if (data.session_id) {
              sessionId.value = data.session_id
            }
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
  // 更新会话列表
  await fetchSessions()
}

const handleKeyPress = (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

const scrollToBottom = async () => {
  await nextTick()
  const messagesContainer = document.querySelector('.messages-feed')
  if (messagesContainer) {
    messagesContainer.scrollTop = messagesContainer.scrollHeight
  }
}

const clearMessages = () => {
  // 重置会话状态，不创建新会话
  let welcomeMessage = '你好！我是学生智能服务助手，有什么可以帮助你的吗？'
  
  // 如果有用户信息，生成个性化欢迎消息
  if (userInfo.value) {
    const { full_name, username, student_id } = userInfo.value
    welcomeMessage = '你好！'
    
    if (full_name) {
      welcomeMessage += full_name
    } else if (username) {
      welcomeMessage += username
    }
    
    if (student_id) {
      welcomeMessage += `（学号：${student_id}）`
    }
    
    welcomeMessage += '，我是学生智能服务助手，有什么可以帮助你的吗？'
  }
  
  messages.value = [{
    id: Date.now(),
    content: welcomeMessage,
    sender: 'ai',
    agentType: 'chat',
    timestamp: new Date().toLocaleTimeString()
  }]
  sessionId.value = null
  selectedSessionId.value = null // 重置选中的会话ID
  currentAgent.value = 'chat'
}

const toggleAgentInfo = () => {
  showAgentInfo.value = !showAgentInfo.value
}

const toggleTheme = () => {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
  document.documentElement.setAttribute('data-theme', theme.value)
}

const fetchUserInfo = async () => {
  try {
    const user = await apiService.get('/auth/me')
    userInfo.value = user
    // 获取用户信息后，生成个性化欢迎消息
    updateWelcomeMessage()
    // 获取用户信息后，加载会话列表
    await fetchSessions()
  } catch (error) {
    console.error('获取用户信息失败:', error)
    // 认证失败时，不强制登出，而是设置用户信息为null
    userInfo.value = null
  }
}

// 更新欢迎消息
const updateWelcomeMessage = () => {
  if (userInfo.value) {
    const { full_name, username, student_id } = userInfo.value
    let welcomeMessage = '你好！'
    
    if (full_name) {
      welcomeMessage += full_name
    } else if (username) {
      welcomeMessage += username
    }
    
    if (student_id) {
      welcomeMessage += `（学号：${student_id}）`
    }
    
    welcomeMessage += '，我是学生智能服务助手，有什么可以帮助你的吗？'
    
    // 更新初始欢迎消息
    if (messages.value.length === 1 && messages.value[0].sender === 'ai') {
      messages.value[0].content = welcomeMessage
    }
  }
}

const handleLogout = () => {
  authService.logout()
  router.push('/login')
}

const fetchSessions = async () => {
  if (!userInfo.value) return
  
  isLoadingSessions.value = true
  try {
    const response = await apiService.get('/sessions')
    sessions.value = response
  } catch (error) {
    console.error('获取会话列表失败:', error)
  } finally {
    isLoadingSessions.value = false
  }
}

const loadSession = async (session) => {
  sessionId.value = session.session_id
  selectedSessionId.value = session.session_id // 更新选中的会话ID
  currentAgent.value = session.current_agent || 'chat'
  currentSessionCreatedAt.value = session.created_at
  
  try {
    const response = await apiService.get(`/session/${session.session_id}/history`)
    const history = response.history
    
    // 转换历史记录格式
    messages.value = history.map((msg, index) => ({
      id: index + 1,
      content: msg.content,
      sender: msg.role === 'user' ? 'user' : 'ai',
      agentType: msg.agent_type || 'chat',
      timestamp: new Date(msg.timestamp).toLocaleTimeString()
    }))
    
    showSessions.value = false
    scrollToBottom()
  } catch (error) {
    console.error('加载会话历史失败:', error)
  }
}

const toggleSessions = () => {
  if (showSessions.value) {
    showSessions.value = false
  } else {
    fetchSessions()
    showSessions.value = true
  }
}

// 删除会话
const deleteSession = async (sessionId) => {
  // 使用更可靠的确认方式
  const userConfirmed = window.confirm('确定要删除这个会话吗？删除后无法恢复。');
  
  if (userConfirmed) {
    try {
      await apiService.delete(`/session/${sessionId}`);
      // 如果删除的是当前选中的会话，重置会话状态
      if (selectedSessionId.value === sessionId) {
        selectedSessionId.value = null;
        clearMessages();
      }
      // 更新会话列表
      await fetchSessions();
    } catch (error) {
      console.error('删除会话失败:', error);
      alert('删除会话失败，请稍后再试');
    }
  }
}

// 切换菜单显示状态
const toggleMenu = () => {
  showMenu.value = !showMenu.value
}

// 打开修改个人信息弹窗
const toggleEditProfile = () => {
  if (userInfo.value) {
    // 填充表单数据
    editProfileForm.value = {
      username: userInfo.value.username || '',
      email: userInfo.value.email || '',
      fullName: userInfo.value.full_name || '',
      studentId: userInfo.value.student_id || '',
      avatar: userInfo.value.avatar || '',
      jwxtUsername: userInfo.value.jwxt_username || '',
      jwxtPassword: userInfo.value.jwxt_password || ''
    }
    showEditProfile.value = true
  }
}

// 关闭修改个人信息弹窗
const closeEditProfile = () => {
  showEditProfile.value = false
}

// 切换修改密码弹窗显示状态
const toggleChangePassword = () => {
  showChangePassword.value = !showChangePassword.value
  showMenu.value = false // 关闭菜单
}

// 关闭修改密码弹窗
const closeChangePassword = () => {
  showChangePassword.value = false
  // 重置表单
  changePasswordForm.value = {
    oldPassword: '',
    newPassword: '',
    confirmPassword: ''
  }
}

// 修改密码
const changePassword = async () => {
  // 验证表单
  if (!changePasswordForm.value.oldPassword || 
      !changePasswordForm.value.newPassword || 
      !changePasswordForm.value.confirmPassword) {
    alert('请填写所有字段')
    return
  }
  
  if (changePasswordForm.value.newPassword !== changePasswordForm.value.confirmPassword) {
    alert('新密码和确认密码不一致')
    return
  }
  
  if (changePasswordForm.value.newPassword.length < 6) {
    alert('新密码长度至少为6位')
    return
  }
  
  isChangingPassword.value = true
  
  try {
    const response = await apiService.post('/auth/change-password', {
      old_password: changePasswordForm.value.oldPassword,
      new_password: changePasswordForm.value.newPassword
    })
    
    // 显示成功提示
    alert('密码修改成功！')
    closeChangePassword()
  } catch (error) {
    console.error('修改密码失败:', error)
    alert('修改密码失败，请检查旧密码是否正确')
  } finally {
    isChangingPassword.value = false
  }
}

// 处理头像上传
const handleAvatarUpload = (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  // 验证文件类型
  if (!file.type.startsWith('image/')) {
    alert('请选择图片文件')
    return
  }
  
  // 验证文件大小（限制为 2MB）
  if (file.size > 2 * 1024 * 1024) {
    alert('图片大小不能超过 2MB')
    return
  }
  
  // 读取文件并转换为 Base64
  const reader = new FileReader()
  reader.onload = (e) => {
    editProfileForm.value.avatar = e.target.result
  }
  reader.readAsDataURL(file)
}

// 更新个人信息
const updateProfile = async () => {
  if (!editProfileForm.value.username || !editProfileForm.value.email) return
  
  isUpdatingProfile.value = true
  
  try {
    const response = await apiService.put('/auth/me', {
      username: editProfileForm.value.username,
      email: editProfileForm.value.email,
      full_name: editProfileForm.value.fullName,
      student_id: editProfileForm.value.studentId,
      avatar: editProfileForm.value.avatar,
      jwxt_username: editProfileForm.value.jwxtUsername,
      jwxt_password: editProfileForm.value.jwxtPassword
    })
    
    // 更新用户信息
    userInfo.value = response
    showEditProfile.value = false
    
    // 显示成功提示
    alert('个人信息更新成功！')
  } catch (error) {
    console.error('更新个人信息失败:', error)
    alert('更新个人信息失败，请稍后再试。')
  } finally {
    isUpdatingProfile.value = false
  }
}

onMounted(async () => {
  const inputElement = document.getElementById('message-input')
  if (inputElement) {
    inputElement.focus()
  }
  scrollToBottom()
  document.documentElement.setAttribute('data-theme', theme.value)
  await fetchUserInfo()
  // 初始化本地欢迎消息，不创建会话
  let welcomeMessage = '你好！我是学生智能服务助手，有什么可以帮助你的吗？'
  if (userInfo.value) {
    const { full_name, username, student_id } = userInfo.value
    welcomeMessage = '你好！'
    if (full_name) {
      welcomeMessage += full_name
    } else if (username) {
      welcomeMessage += username
    }
    if (student_id) {
      welcomeMessage += `（学号：${student_id}）`
    }
    welcomeMessage += '，我是学生智能服务助手，有什么可以帮助你的吗？'
  }
  messages.value = [{
    id: 1,
    content: welcomeMessage,
    sender: 'ai',
    agentType: 'chat',
    timestamp: new Date().toLocaleTimeString()
  }]
})
</script>

<template>
  <div class="app-container">
    <!-- 装饰性背景 -->
    <div class="decorative-bg">
      <div class="bg-indigo"></div>
      <div class="bg-purple"></div>
      <div class="bg-cyan"></div>
      <div class="grid-bg"></div>
    </div>
    
    <!-- 左侧边栏: 对话历史 -->
    <aside class="sidebar">
      <div class="p-[1em] flex flex-col h-full">
        <!-- Logo & New Chat -->
        <div class="sidebar-header">
          <div class="logo">
            <div class="logo-icon">🧠</div>
            <div class="logo-text">
              <h1>文泽奇妙小AI</h1>
              <p>Student v1.0</p>
            </div>
          </div>
          <button class="new-chat-btn" @click="clearMessages">
            <span class="plus-icon">+</span>
            <span class="btn-text">开启新对话</span>
          </button>
        </div>
        <!-- History List -->
        <div class="flex-1 overflow-y-auto">
          <div class="date-header">今日 - {{ new Date().toLocaleDateString('zh-CN') }}</div>
          <!-- More Items -->
          <div v-if="isLoadingSessions" class="loading-sessions">
            <div class="loading-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
          <div v-else-if="sessions.length === 0" class="no-sessions">
            暂无历史会话
          </div>
          <div 
            v-for="session in sessions" 
            :key="session.session_id"
            :class="['session-item', { active: selectedSessionId === session.session_id }]"
          >
            <div class="session-content" @click="loadSession(session)">
              <span class="session-icon">💬</span>
              <div class="session-info">
                <p class="session-name">{{ session.topic || (session.current_agent ? agentsInfo[session.current_agent]?.name || session.current_agent : '通用对话') }}</p>
                <p class="session-time">{{ new Date(session.last_active).toLocaleString('zh-CN') }}</p>
              </div>
            </div>
            <button 
              class="delete-session-btn" 
              @click.stop="deleteSession(session.session_id)"
              title="删除会话"
            >
              ×
            </button>
          </div>
        </div>

      </div>
    </aside>
    
    <!-- 主聊天区域 -->
    <main class="main-chat">
      <!-- Header -->
      <header class="chat-header">
        <div class="header-left">
          <div class="session-info">
            <div class="session-name">{{ currentSessionName }}</div>
            <div class="session-meta">
              <span class="meta-icon">⏰</span>
              <span class="meta-text">会话开始于 {{ currentSessionCreatedAt ? new Date(currentSessionCreatedAt).toLocaleTimeString() : new Date().toLocaleTimeString() }} · 当前时间 {{ new Date().toLocaleString('zh-CN') }}</span>
            </div>
          </div>
        </div>
        <div class="header-right">
          <button class="menu-btn" @click="toggleMenu">•••</button>
          <!-- 下拉菜单 -->
          <div v-if="showMenu" class="dropdown-menu">
            <div class="dropdown-item" @click="toggleChangePassword">修改密码</div>
            <div class="dropdown-item" @click="handleLogout">退出登录</div>
          </div>
        </div>
      </header>
      
      <!-- Messages Feed -->
      <div class="messages-feed custom-scrollbar">
        <div 
          v-for="message in messages" 
          :key="message.id" 
          :class="['message', message.sender === 'user' ? 'user-message' : 'ai-message']"
        >
          <!-- AI Message -->
          <div v-if="message.sender === 'ai'" class="message-avatar ai-avatar">
            <span class="avatar-icon">{{ currentAgentInfo.icon }}</span>
          </div>
          <!-- User Message -->
          <div v-else class="message-avatar user-avatar">
            <img 
              v-if="userInfo?.avatar" 
              :src="userInfo.avatar" 
              alt="头像"
              class="avatar-img"
            />
            <span v-else class="avatar-text">{{ userInfo?.username?.charAt(0) || 'U' }}</span>
          </div>
          
          <div class="message-content-container">
            <!-- AI Message Content -->
            <div v-if="message.sender === 'ai'" class="message-content ai-content">
              <template v-if="message.isStreaming">
                {{ message.content }}<span class="streaming-cursor">|</span>
              </template>
              <div v-else v-html="parseMarkdown(message.content)"></div>
            </div>
            <!-- User Message Content -->
            <div v-else class="message-content user-content">
              {{ message.content }}
            </div>
            

          </div>
        </div>
        

      </div>
      
      <!-- Input Area -->
      <div class="input-area">
        <div class="input-container">
          <!-- Input Box -->
          <div class="input-box">
            <div class="input-controls">
              <textarea
                id="message-input"
                v-model="inputMessage"
                @keypress="handleKeyPress"
                placeholder="发送消息..."
                :disabled="isLoading"
                class="message-input"
                rows="1"
              ></textarea>
              <button @click="sendMessage" :disabled="isLoading" class="send-btn">
                <span class="send-icon">➤</span>
              </button>
            </div>
          </div>
          <p class="copyright">学生智能服务系统 © 2026</p>
        </div>
      </div>
    </main>
    <!-- 修改个人信息弹窗 -->
    <div v-if="showEditProfile" class="modal-overlay" @click="closeEditProfile">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>修改个人信息</h2>
          <button class="close-btn" @click="closeEditProfile">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="updateProfile">
            <div class="form-group">
              <label>头像</label>
              <div class="avatar-upload">
                <div class="avatar-preview">
                  <img 
                    v-if="editProfileForm.avatar" 
                    :src="editProfileForm.avatar" 
                    alt="头像"
                    class="avatar-img"
                  />
                  <div v-else class="avatar-placeholder">
                    <span>{{ userInfo?.username?.charAt(0) || 'U' }}</span>
                  </div>
                </div>
                <input 
                  type="file" 
                  id="avatar" 
                  accept="image/*" 
                  @change="handleAvatarUpload"
                  class="avatar-input"
                />
                <label for="avatar" class="avatar-label">
                  选择图片
                </label>
              </div>
            </div>
            <div class="form-group">
              <label for="username">用户名</label>
              <input 
                type="text" 
                id="username" 
                v-model="editProfileForm.username" 
                placeholder="请输入用户名"
                required
              />
            </div>
            <div class="form-group">
              <label for="email">邮箱</label>
              <input 
                type="email" 
                id="email" 
                v-model="editProfileForm.email" 
                placeholder="请输入邮箱"
                required
              />
            </div>
            <div class="form-group">
              <label for="fullName">姓名</label>
              <input 
                type="text" 
                id="fullName" 
                v-model="editProfileForm.fullName" 
                placeholder="请输入姓名"
              />
            </div>
            <div class="form-group">
              <label for="studentId">学号</label>
              <input 
                type="text" 
                id="studentId" 
                v-model="editProfileForm.studentId" 
                placeholder="请输入学号"
              />
            </div>
            <div class="form-group">
              <label for="jwxtUsername">教务系统账号</label>
              <input 
                type="text" 
                id="jwxtUsername" 
                v-model="editProfileForm.jwxtUsername" 
                placeholder="学号/教务账号"
              />
            </div>
            <div class="form-group">
              <label for="jwxtPassword">教务系统密码</label>
              <input 
                type="password" 
                id="jwxtPassword" 
                v-model="editProfileForm.jwxtPassword" 
                placeholder="教务系统密码"
              />
            </div>
            <div class="form-actions">
              <button type="button" class="cancel-btn" @click="closeEditProfile">取消</button>
              <button type="submit" class="submit-btn" :disabled="isUpdatingProfile">
                {{ isUpdatingProfile ? '更新中...' : '保存修改' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
    
    <!-- 修改密码弹窗 -->
    <div v-if="showChangePassword" class="modal-overlay" @click="closeChangePassword">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>修改密码</h2>
          <button class="close-btn" @click="closeChangePassword">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="changePassword">
            <div class="form-group">
              <label for="oldPassword">旧密码</label>
              <input 
                type="password" 
                id="oldPassword" 
                v-model="changePasswordForm.oldPassword" 
                placeholder="请输入旧密码"
                required
              />
            </div>
            <div class="form-group">
              <label for="newPassword">新密码</label>
              <input 
                type="password" 
                id="newPassword" 
                v-model="changePasswordForm.newPassword" 
                placeholder="请输入新密码（至少6位）"
                required
              />
            </div>
            <div class="form-group">
              <label for="confirmPassword">确认新密码</label>
              <input 
                type="password" 
                id="confirmPassword" 
                v-model="changePasswordForm.confirmPassword" 
                placeholder="请再次输入新密码"
                required
              />
            </div>
            <div class="form-actions">
              <button type="button" class="cancel-btn" @click="closeChangePassword">取消</button>
              <button type="submit" class="submit-btn" :disabled="isChangingPassword">
                {{ isChangingPassword ? '修改中...' : '修改密码' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
    
    <!-- User Profile (Fixed to bottom left) -->
    <div class="user-profile-fixed">
      <div class="profile-info">
        <div class="avatar">
          <img 
            v-if="userInfo?.avatar" 
            :src="userInfo.avatar" 
            alt="头像"
            class="avatar-img"
          />
          <span v-else class="avatar-text">{{ userInfo?.username?.charAt(0) || 'U' }}</span>
          <div class="online-indicator"></div>
        </div>
        <div class="user-details">
          <p class="username">{{ userInfo?.username || '用户' }}</p>
          <p class="user-plan">Student Plan</p>
        </div>
        <span class="edit-profile-btn" @click="toggleEditProfile">✏️</span>
      </div>
    </div>
  </div>
</template>

<style>
/* 全局样式 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-size: 16px;
  line-height: 1.5;
  color: #e2e8f0;
  background-color: #020617;
  overflow: hidden;
}

/* 主容器 */
.app-container {
  height: 100vh;
  display: flex;
  overflow: hidden;
  background-color: #020617;
}

/* 装饰性背景 */
.decorative-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.bg-indigo {
  position: absolute;
  top: -10%;
  left: -10%;
  width: 50%;
  height: 50%;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.35) 0%, rgba(79, 70, 229, 0.15) 40%, transparent 70%);
  border-radius: 50%;
  filter: blur(80px);
  animation: float-glow 8s ease-in-out infinite alternate;
}

.bg-purple {
  position: absolute;
  bottom: -10%;
  right: -10%;
  width: 50%;
  height: 50%;
  background: radial-gradient(circle, rgba(147, 51, 234, 0.35) 0%, rgba(124, 58, 237, 0.15) 40%, transparent 70%);
  border-radius: 50%;
  filter: blur(80px);
  animation: float-glow 10s ease-in-out infinite alternate-reverse;
}

.bg-cyan {
  position: absolute;
  top: 40%;
  left: 30%;
  width: 30%;
  height: 30%;
  background: radial-gradient(circle, rgba(34, 211, 238, 0.2) 0%, transparent 70%);
  border-radius: 50%;
  filter: blur(100px);
  animation: float-glow 12s ease-in-out infinite alternate;
  animation-delay: -3s;
}

.grid-bg {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  opacity: 0.08;
  background-image: 
    linear-gradient(rgba(34, 211, 238, 0.15) 1px, transparent 1px),
    linear-gradient(90deg, rgba(34, 211, 238, 0.15) 1px, transparent 1px);
  background-size: 60px 60px;
  mask-image: radial-gradient(ellipse at center, black 0%, transparent 70%);
  -webkit-mask-image: radial-gradient(ellipse at center, black 0%, transparent 70%);
}

@keyframes float-glow {
  0% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(30px, -20px) scale(1.1); }
  100% { transform: translate(-20px, 30px) scale(0.95); }
}

/* 左侧边栏 */
.sidebar {
  width: 288px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.75) 0%, rgba(15, 23, 42, 0.55) 100%);
  backdrop-filter: blur(20px) saturate(1.2);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 
    0 0 40px rgba(79, 70, 229, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  z-index: 20;
  padding: 12px;
  height: 100vh;
  overflow: hidden;
}

/* 会话列表容器 */
.sidebar .flex-1 {
  overflow-y: auto;
  flex: 1;
  max-height: calc(100vh - 180px);
  scrollbar-width: thin;
  scrollbar-color: rgba(100, 116, 139, 0.5) rgba(15, 23, 42, 0.3);
}

/* 滚动条样式 */
.sidebar .flex-1::-webkit-scrollbar {
  width: 6px;
}

.sidebar .flex-1::-webkit-scrollbar-track {
  background: rgba(15, 23, 42, 0.3);
  border-radius: 3px;
}

.sidebar .flex-1::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.5);
  border-radius: 3px;
}

.sidebar .flex-1::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 116, 139, 0.7);
}

/* 边栏头部 */
.sidebar-header {
  padding: 16px 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 32px;
}

.logo-icon {
  width: 42px;
  height: 42px;
  background: linear-gradient(135deg, #22d3ee 0%, #4f46e5 50%, #7c3aed 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  box-shadow: 
    0 0 20px rgba(34, 211, 238, 0.4),
    0 0 40px rgba(79, 70, 229, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  position: relative;
  overflow: hidden;
}

.logo-icon::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 40%, rgba(255,255,255,0.3) 50%, transparent 60%);
  animation: shimmer 3s ease-in-out infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.logo-text h1 {
  font-size: 20px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.025em;
}

.logo-text p {
  font-size: 10px;
  color: rgba(34, 211, 238, 0.8);
  font-family: monospace;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.new-chat-btn {
  width: 100%;
  padding: 12px 16px;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  color: #ffffff;
  border: none;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 
    0 10px 15px -3px rgba(79, 70, 229, 0.3),
    0 0 20px rgba(79, 70, 229, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
  position: relative;
  overflow: hidden;
}

.new-chat-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
  transform: translateX(-100%);
  transition: transform 0.5s ease;
}

.new-chat-btn:hover::before {
  transform: translateX(100%);
}

.new-chat-btn:hover {
  transform: translateY(-2px);
  box-shadow: 
    0 12px 25px -5px rgba(79, 70, 229, 0.4),
    0 0 30px rgba(124, 58, 237, 0.2);
}

.plus-icon {
  font-size: 20px;
  transition: transform 0.2s ease;
}

.new-chat-btn:hover .plus-icon {
  transform: rotate(90deg);
}

.date-header {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  padding: 8px 12px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  transition: all 0.3s ease;
  border: 1px solid transparent;
  position: relative;
  overflow: hidden;
}

.session-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, #22d3ee, #4f46e5);
  border-radius: 0 3px 3px 0;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.session-content {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.delete-session-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 18px;
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.delete-session-btn:hover {
  background-color: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.3);
}

.session-item:hover {
  background: linear-gradient(90deg, rgba(30, 41, 59, 0.6), rgba(79, 70, 229, 0.08));
  border-color: rgba(34, 211, 238, 0.25);
  box-shadow: 0 0 20px rgba(34, 211, 238, 0.05);
}

.session-item:hover::before {
  opacity: 0.6;
}

.session-item.active {
  background: linear-gradient(90deg, rgba(79, 70, 229, 0.15), rgba(124, 58, 237, 0.08));
  border-color: rgba(79, 70, 229, 0.4);
  box-shadow: 
    0 0 20px rgba(79, 70, 229, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.session-item.active::before {
  opacity: 1;
  box-shadow: 0 0 8px rgba(34, 211, 238, 0.5);
}

.session-icon {
  font-size: 18px;
  color: #64748b;
  transition: color 0.2s ease;
}

.session-item:hover .session-icon {
  color: #22d3ee;
}

.session-item.active .session-icon {
  color: #818cf8;
}

.session-info {
  flex: 1;
  min-width: 0;
}

.session-name {
  font-size: 14px;
  font-weight: 500;
  color: #e2e8f0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-item:hover .session-name {
  color: #f8fafc;
}

.session-time {
  font-size: 10px;
  color: #64748b;
  margin-top: 2px;
}

/* 加载状态 */
.loading-sessions {
  display: flex;
  justify-content: center;
  padding: 32px;
}

.no-sessions {
  text-align: center;
  padding: 32px;
  color: #64748b;
  font-style: italic;
}

/* 用户资料 */
.user-profile {
  padding: 12px 16px;
  border-top: 1px solid rgba(30, 41, 59, 0.5);
  background-color: rgba(15, 23, 42, 0.8);
  margin-top: 8px;
  min-height: 60px;
}

/* 固定在左下角的用户资料 */
.user-profile-fixed {
  position: fixed;
  bottom: 20px;
  left: 20px;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.8) 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 12px 16px;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.4),
    0 0 20px rgba(79, 70, 229, 0.08);
  z-index: 100;
  backdrop-filter: blur(20px) saturate(1.2);
}

.profile-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  border-radius: 12px;
  transition: background-color 0.2s ease;
}

.profile-info:hover {
  background-color: rgba(30, 41, 59, 0.5);
}

.avatar {
  position: relative;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #334155, #1e293b);
  border: 2px solid rgba(79, 70, 229, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 15px rgba(79, 70, 229, 0.2);
}

.avatar-text {
  color: #ffffff;
  font-weight: 500;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.online-indicator {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 14px;
  height: 14px;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  border: 2px solid #020617;
  border-radius: 50%;
  box-shadow: 0 0 10px #22c55e;
  animation: pulse-green 2s ease-in-out infinite;
}

@keyframes pulse-green {
  0%, 100% { box-shadow: 0 0 10px #22c55e; }
  50% { box-shadow: 0 0 20px #22c55e, 0 0 30px rgba(34, 197, 94, 0.3); }
}

.user-details {
  flex: 1;
  min-width: 0;
}

.username {
  font-size: 14px;
  font-weight: 700;
  color: #ffffff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-plan {
  font-size: 10px;
  color: #64748b;
  margin-top: 2px;
}

.edit-profile-btn {
  font-size: 18px;
  color: #94a3b8;
  cursor: pointer;
  transition: color 0.2s ease;
}

.edit-profile-btn:hover {
  color: #22d3ee;
}

/* 弹窗样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  width: 100%;
  max-width: 480px;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.modal-header h2 {
  font-size: 18px;
  font-weight: 700;
  color: #ffffff;
}

.close-btn {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 24px;
  cursor: pointer;
  transition: color 0.2s ease;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
}

.close-btn:hover {
  color: #ffffff;
  background-color: rgba(255, 255, 255, 0.05);
}

.modal-body {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #e2e8f0;
  margin-bottom: 8px;
}

.form-group input {
  width: 100%;
  padding: 10px 12px;
  background-color: rgba(30, 41, 59, 0.5);
  border: 1px solid #334155;
  border-radius: 8px;
  color: #e2e8f0;
  font-size: 14px;
  transition: all 0.2s ease;
}

.form-group input:focus {
  outline: none;
  border-color: rgba(34, 211, 238, 0.5);
  background-color: #1e293b;
}

/* 头像上传样式 */
.avatar-upload {
  display: flex;
  align-items: center;
  gap: 16px;
}

.avatar-preview {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  overflow: hidden;
  border: 2px solid #334155;
  background-color: #1e293b;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #334155;
  color: #ffffff;
  font-size: 32px;
  font-weight: 700;
}

.avatar-input {
  display: none;
}

.avatar-label {
  padding: 8px 16px;
  background-color: #4f46e5;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
}

.avatar-label:hover {
  background-color: #4338ca;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(79, 70, 229, 0.4);
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
}

.cancel-btn {
  padding: 10px 20px;
  background: transparent;
  border: 1px solid #334155;
  border-radius: 8px;
  color: #e2e8f0;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.cancel-btn:hover {
  border-color: rgba(34, 211, 238, 0.5);
  background-color: rgba(34, 211, 238, 0.05);
}

.submit-btn {
  padding: 10px 20px;
  background-color: #4f46e5;
  border: none;
  border-radius: 8px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
}

.submit-btn:hover:not(:disabled) {
  background-color: #4338ca;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(79, 70, 229, 0.4);
}

.submit-btn:disabled {
  background-color: #64748b;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

/* 主聊天区域 */
.main-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 10;
  background: linear-gradient(to bottom, transparent, rgba(15, 23, 42, 0.3));
}

/* 聊天头部 */
.chat-header {
  height: 64px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.8) 0%, rgba(15, 23, 42, 0.5) 100%);
  backdrop-filter: blur(20px) saturate(1.2);
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.2),
    inset 0 -1px 0 rgba(255, 255, 255, 0.03);
  position: relative;
}

.chat-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 5%;
  right: 5%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(34, 211, 238, 0.3), rgba(124, 58, 237, 0.3), transparent);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-right {
  position: relative;
  display: flex;
  align-items: center;
}

.session-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.session-info .session-name {
  font-size: 14px;
  font-weight: 700;
  color: #ffffff;
}

.session-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: #64748b;
}

.meta-icon {
  font-size: 12px;
}

.menu-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(30, 41, 59, 0.5);
  color: #94a3b8;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.menu-btn:hover {
  background: rgba(79, 70, 229, 0.2);
  border-color: rgba(79, 70, 229, 0.4);
  color: #ffffff;
  box-shadow: 0 0 15px rgba(79, 70, 229, 0.3);
}

/* 下拉菜单 */
.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 12px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(15, 23, 42, 0.9) 100%);
  backdrop-filter: blur(24px) saturate(1.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  box-shadow: 
    0 20px 40px rgba(0, 0, 0, 0.4),
    0 0 30px rgba(79, 70, 229, 0.1);
  min-width: 180px;
  z-index: 1000;
  overflow: hidden;
}

.dropdown-menu::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(34, 211, 238, 0.4), transparent);
}

.dropdown-item {
  padding: 12px 18px;
  color: #e2e8f0;
  cursor: pointer;
  transition: all 0.3s ease;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  position: relative;
}

.dropdown-item:last-child {
  border-bottom: none;
}

.dropdown-item:hover {
  background: linear-gradient(90deg, rgba(79, 70, 229, 0.15), rgba(124, 58, 237, 0.08));
  color: #ffffff;
  padding-left: 22px;
}



/* 消息区域 */
.messages-feed {
  flex: 1;
  overflow-y: auto;
  padding: 32px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* 消息 */
.message {
  display: flex;
  gap: 16px;
  max-width: 4xl;
  margin: 0 auto;
  width: 100%;
}

.user-message {
  flex-direction: row-reverse;
}

/* 消息头像 */
.message-avatar {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
}

.ai-avatar {
  background: linear-gradient(135deg, #22d3ee 0%, #4f46e5 100%);
  box-shadow: 
    0 0 20px rgba(34, 211, 238, 0.3),
    0 0 40px rgba(79, 70, 229, 0.15);
  border: none;
}

.user-avatar {
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.3), rgba(124, 58, 237, 0.3));
  border: 2px solid rgba(139, 92, 246, 0.4);
  box-shadow: 0 0 15px rgba(124, 58, 237, 0.2);
}

.avatar-icon {
  color: #ffffff;
  font-size: 20px;
}

/* 消息内容容器 */
.message-content-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 消息内容 */
.message-content {
  padding: 20px;
  border-radius: 18px;
  line-height: 1.6;
  word-wrap: break-word;
  position: relative;
}

.ai-content {
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%);
  border: 1px solid rgba(34, 211, 238, 0.15);
  border-top-left-radius: 4px;
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.05),
    0 0 30px rgba(34, 211, 238, 0.03);
}

.ai-content::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  background: linear-gradient(180deg, #22d3ee, #4f46e5, transparent);
  border-radius: 0 3px 3px 0;
  opacity: 0.6;
}

.user-content {
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.25) 0%, rgba(124, 58, 237, 0.2) 100%);
  border: 1px solid rgba(139, 92, 246, 0.25);
  border-top-right-radius: 4px;
  color: #f8fafc;
  align-self: flex-end;
  margin-left: 48px;
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.08),
    0 0 30px rgba(124, 58, 237, 0.05);
}

.user-content::before {
  content: '';
  position: absolute;
  right: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  background: linear-gradient(180deg, #a78bfa, #7c3aed, transparent);
  border-radius: 3px 0 0 3px;
  opacity: 0.5;
}



/* 输入区域 */
.input-area {
  padding: 24px 32px 0;
}

.input-container {
  max-width: 4xl;
  margin: 0 auto;
  width: 100%;
}

.input-box {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.6) 100%);
  backdrop-filter: blur(20px) saturate(1.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 8px;
  transition: all 0.3s ease;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  position: relative;
}

.input-box::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: 20px;
  padding: 1px;
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.3), rgba(124, 58, 237, 0.3), rgba(79, 70, 229, 0.3));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.input-box:focus-within::before {
  opacity: 1;
}

.input-box:focus-within {
  border-color: rgba(34, 211, 238, 0.3);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.3),
    0 0 30px rgba(34, 211, 238, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.input-controls {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 12px 16px;
}

.message-input {
  flex: 1;
  background: transparent;
  border: none;
  color: #e2e8f0;
  font-size: 16px;
  line-height: 1.4;
  padding: 10px 0;
  resize: none;
  max-height: 192px;
  font-family: inherit;
}

.message-input:focus {
  outline: none;
}

.message-input::placeholder {
  color: #64748b;
}

.send-btn {
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  color: #ffffff;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 
    0 4px 15px rgba(79, 70, 229, 0.4),
    0 0 20px rgba(124, 58, 237, 0.2);
  position: relative;
  overflow: hidden;
}

.send-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent, rgba(255,255,255,0.2), transparent);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.send-btn:hover:not(:disabled)::before {
  opacity: 1;
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.08) rotate(-5deg);
  box-shadow: 
    0 6px 20px rgba(79, 70, 229, 0.5),
    0 0 30px rgba(124, 58, 237, 0.3);
}

.send-btn:active:not(:disabled) {
  transform: scale(0.95);
}

.send-btn:disabled {
  background: linear-gradient(135deg, #475569, #64748b);
  cursor: not-allowed;
  box-shadow: none;
}

.send-icon {
  font-size: 20px;
}

.copyright {
  text-align: center;
  font-size: 10px;
  color: #64748b;
  margin-top: 12px;
  margin-bottom: 32px;
}

/* 滚动条样式 */
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(34, 211, 238, 0.3);
}

/* 动画 */
@keyframes neon-pulse {
  0%, 100% { box-shadow: 0 0 5px rgba(34, 211, 238, 0.4), 0 0 10px rgba(34, 211, 238, 0.2); }
  50% { box-shadow: 0 0 15px rgba(34, 211, 238, 0.6), 0 0 25px rgba(34, 211, 238, 0.3); }
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}

/* 加载动画 */
.loading-dots {
  display: flex;
  gap: 4px;
  padding: 8px 0;
  justify-content: center;
}

.loading-dots span {
  width: 8px;
  height: 8px;
  background: #22d3ee;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

/* 流式光标 */
.streaming-cursor {
  display: inline-block;
  animation: blink 1s infinite;
  margin-left: 2px;
  color: #22d3ee;
  font-weight: bold;
}

/* Markdown 样式 */
.ai-content h1, .ai-content h2, .ai-content h3, .ai-content h4, .ai-content h5, .ai-content h6 {
  color: #ffffff;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  font-weight: 600;
}

.ai-content h1 {
  font-size: 1.8em;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 0.3em;
}

.ai-content h2 {
  font-size: 1.5em;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 0.3em;
}

.ai-content h3 {
  font-size: 1.2em;
}

.ai-content ul, .ai-content ol {
  margin-left: 2em;
  margin-top: 0.5em;
  margin-bottom: 0.5em;
}

.ai-content li {
  margin-bottom: 0.3em;
}

.ai-content code {
  background-color: rgba(255, 255, 255, 0.1);
  padding: 0.2em 0.4em;
  border-radius: 4px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.9em;
  color: #f8fafc;
}

.ai-content pre {
  background-color: rgba(0, 0, 0, 0.3);
  padding: 1em;
  border-radius: 8px;
  overflow-x: auto;
  margin: 1em 0;
}

.ai-content pre code {
  background-color: transparent;
  padding: 0;
  font-size: 0.85em;
  line-height: 1.4;
}

.ai-content a {
  color: #38bdf8;
  text-decoration: none;
  transition: color 0.2s ease;
}

.ai-content a:hover {
  color: #22d3ee;
  text-decoration: underline;
}

.ai-content blockquote {
  border-left: 4px solid #4f46e5;
  padding-left: 1em;
  margin: 1em 0;
  color: #94a3b8;
  font-style: italic;
}

.ai-content table {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
}

.ai-content th, .ai-content td {
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 0.5em;
  text-align: left;
}

.ai-content th {
  background-color: rgba(79, 70, 229, 0.1);
  font-weight: 600;
}

.ai-content tr:nth-child(even) {
  background-color: rgba(255, 255, 255, 0.05);
}

.ai-content hr {
  border: none;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  margin: 2em 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    width: 64px;
  }
  
  .sidebar-header, .search-container, .user-details, .btn-text, .session-name, .session-time, .date-header {
    display: none;
  }
  
  .logo-icon, .avatar {
    margin: 0 auto;
  }
  
  .main-chat {
    flex: 1;
  }
  
  .chat-header, .input-area {
    padding: 0 16px;
  }
  
  .messages-feed {
    padding: 16px;
  }
  
  .message {
    max-width: 100%;
  }
  
  .user-content {
    margin-left: 0;
  }
}

@media (max-width: 480px) {
  .messages-feed {
    gap: 16px;
  }
  
  .message-content {
    padding: 12px;
  }
  
  .share-text {
    display: none;
  }
}
</style>
