<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { authService } from '../services/authService'
import AdminDashboard from './AdminDashboard.vue'
import KnowledgeBase from './KnowledgeBase.vue'

const router = useRouter()
const activeMenu = ref('overview')
const userInfo = ref(null)

const menuItems = [
  { key: 'overview', label: '概览统计', icon: '📊' },
  { key: 'users', label: '用户统计', icon: '👥' },
  { key: 'agents', label: '智能体统计', icon: '🤖' },
  { key: 'knowledge', label: '知识库管理', icon: '📚' }
]

const checkAdmin = async () => {
  try {
    const user = await authService.getCurrentUser()
    if (!user.is_admin) {
      router.push('/chat')
      return
    }
    userInfo.value = user
  } catch (error) {
    authService.logout()
    router.push('/login')
  }
}

const handleLogout = () => {
  authService.logout()
  router.push('/login')
}

onMounted(() => {
  checkAdmin()
})
</script>

<template>
  <div class="admin-page">
    <!-- 左侧侧边栏 -->
    <aside class="admin-sidebar">
      <div class="sidebar-header">
        <div class="admin-logo">⚙️</div>
        <div class="admin-brand">
          <h2>管理后台</h2>
          <p>Admin Dashboard</p>
        </div>
      </div>
      
      <nav class="admin-menu">
        <div
          v-for="item in menuItems"
          :key="item.key"
          :class="['menu-item', { active: activeMenu === item.key }]"
          @click="activeMenu = item.key"
        >
          <span class="menu-icon">{{ item.icon }}</span>
          <span class="menu-label">{{ item.label }}</span>
        </div>
      </nav>
      
      <div class="sidebar-footer">
        <div class="admin-user">
          <div class="user-avatar">{{ userInfo?.username?.charAt(0) || 'A' }}</div>
          <div class="user-info">
            <p class="user-name">{{ userInfo?.username || '管理员' }}</p>
            <p class="user-role">Administrator</p>
          </div>
        </div>
        <button class="logout-btn" @click="handleLogout">
          <span>🚪</span> 退出
        </button>
      </div>
    </aside>
    
    <!-- 右侧主内容区 -->
    <main class="admin-main">
      <div class="admin-content">
        <AdminDashboard :active-tab="activeMenu" v-if="activeMenu !== 'knowledge'" />
        <KnowledgeBase v-if="activeMenu === 'knowledge'" />
      </div>
    </main>
  </div>
</template>

<style scoped>
.admin-page {
  display: flex;
  height: 100vh;
  background: #020617;
  color: #e2e8f0;
  overflow: hidden;
}

/* 左侧侧边栏 */
.admin-sidebar {
  width: 260px;
  flex-shrink: 0;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(15, 23, 42, 0.85) 100%);
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(20px) saturate(1.2);
  box-shadow: 
    0 0 40px rgba(79, 70, 229, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  position: relative;
  overflow: hidden;
}

.admin-sidebar::before {
  content: '';
  position: absolute;
  top: -20%;
  left: -20%;
  width: 60%;
  height: 40%;
  background: radial-gradient(circle, rgba(79, 70, 229, 0.15) 0%, transparent 70%);
  filter: blur(60px);
  pointer-events: none;
}

.sidebar-header {
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  gap: 12px;
}

.admin-logo {
  width: 42px;
  height: 42px;
  background: linear-gradient(135deg, #22d3ee 0%, #4f46e5 50%, #7c3aed 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  box-shadow: 
    0 0 20px rgba(79, 70, 229, 0.4),
    0 0 40px rgba(34, 211, 238, 0.15);
  position: relative;
  overflow: hidden;
}

.admin-logo::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 40%, rgba(255,255,255,0.25) 50%, transparent 60%);
  animation: shimmer 3s ease-in-out infinite;
}

.admin-brand h2 {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
}

.admin-brand p {
  font-size: 11px;
  color: #64748b;
  margin: 2px 0 0;
  font-family: monospace;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* 菜单 */
.admin-menu {
  flex: 1;
  padding: 16px 12px;
  overflow-y: auto;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #94a3b8;
  font-size: 14px;
  margin-bottom: 4px;
}

.menu-item:hover {
  background: rgba(255, 255, 255, 0.04);
  color: #e2e8f0;
}

.menu-item.active {
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.9) 0%, rgba(124, 58, 237, 0.9) 100%);
  color: #ffffff;
  box-shadow: 
    0 4px 20px rgba(79, 70, 229, 0.4),
    0 0 30px rgba(124, 58, 237, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(139, 92, 246, 0.3);
  position: relative;
  overflow: hidden;
}

.menu-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, #22d3ee, #4f46e5);
  border-radius: 0 3px 3px 0;
  box-shadow: 0 0 8px rgba(34, 211, 238, 0.5);
}

.menu-icon {
  font-size: 18px;
  width: 24px;
  text-align: center;
}

/* 底部用户信息 */
.sidebar-footer {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.admin-user {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.user-avatar {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #22d3ee 0%, #4f46e5 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 13px;
  font-weight: 500;
  color: #e2e8f0;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-role {
  font-size: 11px;
  color: #64748b;
  margin: 2px 0 0;
}

.logout-btn {
  width: 100%;
  padding: 8px 12px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 8px;
  color: #ef4444;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.logout-btn:hover {
  background: rgba(239, 68, 68, 0.2);
}

/* 右侧主内容区 */
.admin-main {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

/* 滚动条 */
.admin-content::-webkit-scrollbar,
.admin-menu::-webkit-scrollbar {
  width: 6px;
}

.admin-content::-webkit-scrollbar-track,
.admin-menu::-webkit-scrollbar-track {
  background: transparent;
}

.admin-content::-webkit-scrollbar-thumb,
.admin-menu::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.3);
  border-radius: 3px;
}

/* 响应式 */
@media (max-width: 768px) {
  .admin-sidebar {
    width: 200px;
  }
  .admin-content {
    padding: 16px;
  }
}
</style>
