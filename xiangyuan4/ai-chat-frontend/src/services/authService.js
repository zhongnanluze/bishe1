// 认证服务

const API_BASE_URL = 'http://localhost:8000/api/auth'

class AuthService {
  // 截断密码到72字节
  truncatePassword(password) {
    let truncated = password
    let bytes = new Blob([truncated]).size
    while (bytes > 72 && truncated.length > 0) {
      truncated = truncated.slice(0, -1)
      bytes = new Blob([truncated]).size
    }
    return truncated
  }

  // 免密快捷登录（开发测试用）
  async easyLogin(username) {
    const response = await fetch(`${API_BASE_URL}/easy-login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username,
        password: ''
      })
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || '快捷登录失败')
    }

    return await response.json()
  }

  // 登录
  async login(username, password) {
    // 自动截断密码到72字节
    const truncatedPassword = this.truncatePassword(password)
    
    const response = await fetch(`${API_BASE_URL}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username,
        password: truncatedPassword
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
    // 自动截断密码到72字节
    const truncatedPassword = this.truncatePassword(userData.password)
    const truncatedUserData = {
      ...userData,
      password: truncatedPassword
    }
    
    const response = await fetch(`${API_BASE_URL}/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(truncatedUserData)
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

    // 自动截断密码到72字节
    const truncatedOldPassword = this.truncatePassword(oldPassword)
    const truncatedNewPassword = this.truncatePassword(newPassword)

    const response = await fetch(`${API_BASE_URL}/change-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        old_password: truncatedOldPassword,
        new_password: truncatedNewPassword
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