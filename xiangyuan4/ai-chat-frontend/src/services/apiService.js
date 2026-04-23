// API 服务
import { authService } from './authService'

const API_BASE_URL = 'http://localhost:8000/api'

class ApiService {
  // 通用请求方法
  async request(endpoint, options = {}) {
    const token = authService.getAccessToken()
    
    const defaultHeaders = {}
    
    // 如果是 FormData，不设置 Content-Type，让浏览器自动处理 boundary
    if (!(options.body instanceof FormData)) {
      defaultHeaders['Content-Type'] = 'application/json'
    }
    
    if (token) {
      defaultHeaders['Authorization'] = `Bearer ${token}`
    }
    
    const config = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers
      }
    }
    
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, config)
      
      // 检查响应状态
      if (!response.ok) {
        // 处理 401 错误（令牌过期）
        if (response.status === 401) {
          try {
            // 尝试刷新令牌
            const refreshToken = authService.getRefreshToken()
            if (refreshToken) {
              const refreshResponse = await authService.refreshToken(refreshToken)
              
              if (refreshResponse && refreshResponse.access_token) {
                // 保存新令牌
                authService.saveTokens(
                  refreshResponse.access_token,
                  refreshResponse.refresh_token
                )
                
                // 重新发送请求
                config.headers['Authorization'] = `Bearer ${refreshResponse.access_token}`
                const retryResponse = await fetch(`${API_BASE_URL}${endpoint}`, config)
                
                if (!retryResponse.ok) {
                  throw new Error(`请求失败: ${retryResponse.status}`)
                }
                
                return await retryResponse.json()
              }
            }
            
            // 刷新令牌失败，清除本地存储
            authService.logout()
            window.location.href = '/login'
            throw new Error('登录已过期，请重新登录')
          } catch (refreshError) {
            authService.logout()
            window.location.href = '/login'
            throw refreshError
          }
        }
        
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `请求失败: ${response.status}`)
      }
      
      return await response.json()
    } catch (error) {
      throw error
    }
  }

  // GET 请求
  async get(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString()
    const url = queryString ? `${endpoint}?${queryString}` : endpoint
    
    return this.request(url, {
      method: 'GET'
    })
  }

  // POST 请求
  async post(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data)
    })
  }

  // PUT 请求
  async put(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data)
    })
  }

  // DELETE 请求
  async delete(endpoint) {
    return this.request(endpoint, {
      method: 'DELETE'
    })
  }

  // 流式请求
  async stream(endpoint, data = {}) {
    const token = authService.getAccessToken()
    
    const headers = {
      'Content-Type': 'application/json'
    }
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data)
    })
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `请求失败: ${response.status}`)
    }
    
    return response.body
  }

  // 知识库相关方法
  async getKnowledgeBase(agentType = null) {
    const params = agentType ? { agent_type: agentType } : {}
    return this.get('/knowledge-base', params)
  }

  async addKnowledgeBaseItem(item) {
    return this.post('/knowledge-base', item)
  }

  async deleteKnowledgeBaseItem(id) {
    return this.delete(`/knowledge-base/${id}`)
  }
}

export const apiService = new ApiService()