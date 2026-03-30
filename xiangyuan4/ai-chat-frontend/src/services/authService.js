// 认证服务

const API_BASE_URL = 'http://localhost:8000/api/auth'

class AuthService {
  // 登录
  async login(username, password) {
    const response = await fetch(`${API_BASE_URL}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username,
        password
      })
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || '登录失败')
    }

    return await response.json()
  }

  // 注册
  async register(userData) {
    const response = await fetch(`${API_BASE_URL}/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(userData)
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || '注册失败')
    }

    return await response.json()
  }

  // 刷新令牌
  async refreshToken(refreshToken) {
    const response = await fetch(`${API_BASE_URL}/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        refresh_token: refreshToken
      })
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || '刷新令牌失败')
    }

    return await response.json()
  }

  // 获取当前用户信息
  async getCurrentUser() {
    const token = localStorage.getItem('access_token')
    if (!token) {
      throw new Error('未登录')
    }

    const response = await fetch(`${API_BASE_URL}/me`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || '获取用户信息失败')
    }

    return await response.json()
  }

  // 修改密码
  async changePassword(oldPassword, newPassword) {
    const token = localStorage.getItem('access_token')
    if (!token) {
      throw new Error('未登录')
    }

    const response = await fetch(`${API_BASE_URL}/change-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        old_password: oldPassword,
        new_password: newPassword
      })
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || '修改密码失败')
    }

    return await response.json()
  }

  // 登出
  logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  // 检查是否已登录
  isLoggedIn() {
    return !!localStorage.getItem('access_token')
  }

  // 获取访问令牌
  getAccessToken() {
    return localStorage.getItem('access_token')
  }

  // 获取刷新令牌
  getRefreshToken() {
    return localStorage.getItem('refresh_token')
  }

  // 保存令牌
  saveTokens(accessToken, refreshToken) {
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('refresh_token', refreshToken)
  }
}

export const authService = new AuthService()