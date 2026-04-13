// 路由配置
import { createRouter, createWebHistory } from 'vue-router'
import { authService } from '../services/authService'

// 导入页面组件
const Login = () => import('../views/Login.vue')
const Register = () => import('../views/Register.vue')
const Chat = () => import('../views/Chat.vue')
const Debug = () => import('../views/Debug.vue')
const KnowledgeBase = () => import('../views/KnowledgeBase.vue')

const routes = [
  {
    path: '/',
    redirect: '/debug'
  },
  {
    path: '/debug',
    name: 'Debug',
    component: Debug
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: {
      requiresGuest: true
    }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: {
      requiresGuest: true
    }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: Chat,
    meta: {
      requiresAuth: true
    }
  },
  {
    path: '/knowledge-base',
    name: 'KnowledgeBase',
    component: KnowledgeBase,
    meta: {
      requiresAuth: true
    }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/debug'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const isAuthenticated = authService.isLoggedIn()
  console.log('=== 路由守卫开始 ===')
  console.log('目标路径:', to.path)
  console.log('路由名称:', to.name)
  console.log('路由meta:', to.meta)
  console.log('是否已登录:', isAuthenticated)
  console.log('本地存储access_token:', localStorage.getItem('access_token'))
  console.log('是否需要认证:', to.matched.some(record => record.meta.requiresAuth))
  console.log('是否需要访客状态:', to.matched.some(record => record.meta.requiresGuest))
  
  if (to.matched.some(record => record.meta.requiresAuth)) {
    console.log('-> 需要认证')
    if (!isAuthenticated) {
      console.log('-> 未登录，跳转到登录页面')
      next({ name: 'Login' })
    } else {
      console.log('-> 已登录，验证 token 有效性')
      try {
        await authService.getCurrentUser()
        console.log('-> Token 有效，继续')
        next()
      } catch (error) {
        console.log('-> Token 无效，清除登录状态并跳转到登录页面')
        authService.logout()
        next({ name: 'Login' })
      }
    }
  } 
  else if (to.matched.some(record => record.meta.requiresGuest)) {
    console.log('-> 需要访客状态')
    if (isAuthenticated) {
      console.log('-> 已登录，跳转到聊天页面')
      next({ name: 'Chat' })
    } else {
      console.log('-> 未登录，继续')
      next()
    }
  }
  else {
    console.log('-> 其他路由，直接通过')
    next()
  }
  console.log('=== 路由守卫结束 ===')
})

export default router