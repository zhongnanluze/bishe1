<script setup>
import { ref, onMounted, computed } from 'vue'
import { apiService } from '../services/apiService'

const knowledgeBaseItems = ref([])
const isLoading = ref(false)
const isAdding = ref(false)
const isSearching = ref(false)
const isUploading = ref(false)
const uploadError = ref('')
const searchQuery = ref('')
const searchResults = ref([])
const vectorStatus = ref({ vector_count: 0, collection: '' })
const newItem = ref({
  title: '',
  content: '',
  category: ''
})
const showAddForm = ref(false)
const showDeleteConfirm = ref(false)
const deleteTargetId = ref(null)

// 分类颜色映射
const categoryColors = {
  '校园生活': '#22d3ee',
  '学业相关': '#a78bfa',
  '学生事务': '#f472b6',
  '规章制度': '#fbbf24',
  '办事指南': '#34d399',
}

const getCategoryColor = (cat) => {
  return categoryColors[cat] || '#64748b'
}

// 内容预览截断
const previewContent = (content, maxLen = 120) => {
  if (!content) return ''
  const text = content.replace(/\n/g, ' ')
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text
}

// 加载知识库数据
const loadKnowledgeBase = async () => {
  isLoading.value = true
  try {
    const response = await apiService.getKnowledgeBase()
    knowledgeBaseItems.value = Array.isArray(response) ? response : (response.data || [])
  } catch (error) {
    console.error('加载知识库失败:', error)
  } finally {
    isLoading.value = false
  }
}

// 语义搜索
const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    searchResults.value = []
    return
  }
  isSearching.value = true
  try {
    const response = await apiService.post('/knowledge-base/search', {
      query: searchQuery.value.trim(),
      top_k: 5
    })
    searchResults.value = response.results || []
  } catch (error) {
    console.error('搜索失败:', error)
    alert('搜索失败，请稍后重试')
  } finally {
    isSearching.value = false
  }
}

// 获取向量库状态
const loadVectorStatus = async () => {
  try {
    const response = await apiService.get('/knowledge-base/status')
    vectorStatus.value = response
  } catch (error) {
    console.error('获取向量状态失败:', error)
  }
}

// 文件上传
const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  const allowedTypes = ['.txt', '.md', '.pdf', '.docx']
  const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  if (!allowedTypes.includes(ext)) {
    uploadError.value = '仅支持 txt, md, pdf, docx 格式'
    return
  }

  if (file.size > 10 * 1024 * 1024) {
    uploadError.value = '文件大小不能超过 10MB'
    return
  }

  isUploading.value = true
  uploadError.value = ''

  const formData = new FormData()
  formData.append('file', file)

  try {
    await apiService.request('/knowledge-base/upload', {
      method: 'POST',
      body: formData,
      headers: {}
    })
    event.target.value = ''
    await loadKnowledgeBase()
    await loadVectorStatus()
  } catch (error) {
    console.error('上传失败:', error)
    uploadError.value = error.message || '上传失败，请稍后重试'
  } finally {
    isUploading.value = false
  }
}

// 添加知识库项
const addKnowledgeBaseItem = async () => {
  if (!newItem.value.title || !newItem.value.content) {
    alert('标题和内容不能为空')
    return
  }
  
  isAdding.value = true
  try {
    await apiService.addKnowledgeBaseItem(newItem.value)
    await loadKnowledgeBase()
    newItem.value = { title: '', content: '', category: '' }
    showAddForm.value = false
    await loadVectorStatus()
  } catch (error) {
    console.error('添加知识库项失败:', error)
  } finally {
    isAdding.value = false
  }
}

// 删除确认
const confirmDelete = (id) => {
  deleteTargetId.value = id
  showDeleteConfirm.value = true
}

const cancelDelete = () => {
  showDeleteConfirm.value = false
  deleteTargetId.value = null
}

const executeDelete = async () => {
  if (!deleteTargetId.value) return
  try {
    await apiService.deleteKnowledgeBaseItem(deleteTargetId.value)
    await loadKnowledgeBase()
    await loadVectorStatus()
  } catch (error) {
    console.error('删除知识库项失败:', error)
  } finally {
    showDeleteConfirm.value = false
    deleteTargetId.value = null
  }
}

onMounted(() => {
  loadKnowledgeBase()
  loadVectorStatus()
})
</script>

<template>
  <div class="kb-page">
    <!-- 装饰性背景 -->
    <div class="decorative-bg">
      <div class="bg-blob bg-blob-1"></div>
      <div class="bg-blob bg-blob-2"></div>
      <div class="grid-bg"></div>
    </div>

    <div class="kb-container">
      <!-- Header -->
      <header class="kb-header">
        <div class="header-left">
          <div class="logo-icon">📚</div>
          <div>
            <h1 class="kb-title">知识库管理</h1>
            <p class="kb-subtitle">上传文档、搜索知识、构建你的校园智能问答库</p>
          </div>
        </div>
        <div class="header-right">
          <div class="status-badge">
            <span class="status-dot"></span>
            <span class="status-text">{{ vectorStatus.vector_count || 0 }} 个向量片段</span>
          </div>
          <button class="btn-primary" @click="showAddForm = !showAddForm">
            <span class="btn-icon">{{ showAddForm ? '✕' : '+' }}</span>
            <span>{{ showAddForm ? '收起' : '添加知识' }}</span>
          </button>
        </div>
      </header>

      <!-- 搜索区 -->
      <div class="search-section">
        <div class="search-box" :class="{ 'search-focused': false }">
          <span class="search-icon">🔍</span>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="输入关键词，语义搜索知识库..."
            @keyup.enter="handleSearch"
            class="search-input"
          />
          <button @click="handleSearch" :disabled="isSearching" class="search-btn">
            {{ isSearching ? '搜索中...' : '搜索' }}
          </button>
        </div>
        <p v-if="searchResults.length > 0" class="search-tip">
          找到 {{ searchResults.length }} 条相关结果
          <a href="#" @click.prevent="searchResults = []" class="clear-link">清除</a>
        </p>
      </div>

      <!-- 搜索结果 -->
      <transition-group name="fade-up" tag="div" v-if="searchResults.length > 0" class="results-section">
        <div v-for="(result, index) in searchResults" :key="'r' + index" class="result-card">
          <div class="result-glow"></div>
          <div class="result-body">
            <div class="result-top">
              <h4 class="result-title">{{ result.title || '未命名' }}</h4>
              <div class="similarity-bar">
                <div class="similarity-fill" :style="{ width: (result.similarity * 100) + '%' }"></div>
                <span class="similarity-text">{{ (result.similarity * 100).toFixed(1) }}%</span>
              </div>
            </div>
            <p class="result-text">{{ result.content }}</p>
            <div class="result-meta">
              <span v-if="result.category" class="meta-tag" :style="{ color: getCategoryColor(result.category) }">
                {{ result.category }}
              </span>
            </div>
          </div>
        </div>
      </transition-group>

      <!-- 添加表单 -->
      <transition name="expand">
        <div v-if="showAddForm" class="add-panel">
          <div class="panel-glow"></div>
          <div class="add-panel-inner">
            <h3 class="panel-title">📝 添加新知识</h3>
            <div class="add-grid">
              <!-- 左侧：手动输入 -->
              <div class="add-col">
                <label class="field-label">标题</label>
                <input v-model="newItem.title" type="text" placeholder="如：图书馆开放时间" class="field-input" />
                
                <label class="field-label">分类</label>
                <input v-model="newItem.category" type="text" placeholder="如：校园生活 / 学业相关" class="field-input" />
                
                <label class="field-label">内容</label>
                <textarea v-model="newItem.content" placeholder="输入知识内容..." rows="5" class="field-textarea"></textarea>
                
                <button class="btn-submit" @click="addKnowledgeBaseItem" :disabled="isAdding">
                  <span v-if="isAdding">⏳ 保存中...</span>
                  <span v-else>💾 保存到知识库</span>
                </button>
              </div>

              <!-- 右侧：文件上传 -->
              <div class="add-col upload-col">
                <div class="upload-card">
                  <div class="upload-icon">📁</div>
                  <h4>上传文件</h4>
                  <p class="upload-desc">支持 TXT、Markdown、PDF、Word</p>
                  <input
                    type="file"
                    id="kb-file"
                    accept=".txt,.md,.pdf,.docx"
                    @change="handleFileUpload"
                    class="hidden-input"
                  />
                  <label for="kb-file" class="btn-upload">
                    {{ isUploading ? '解析中...' : '选择文件' }}
                  </label>
                  <p class="upload-limit">单个文件不超过 10MB</p>
                  <p v-if="uploadError" class="upload-error">{{ uploadError }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </transition>

      <!-- 列表区 -->
      <div class="list-section">
        <div class="list-header">
          <h3>📋 知识列表</h3>
          <span class="list-count">{{ knowledgeBaseItems.length }} 条</span>
        </div>

        <div v-if="isLoading" class="loading-state">
          <div class="spinner"></div>
          <p>加载中...</p>
        </div>

        <div v-else-if="knowledgeBaseItems.length === 0" class="empty-state">
          <div class="empty-icon">📝</div>
          <h4>知识库还是空的</h4>
          <p>点击右上角「添加知识」开始构建你的智能问答库</p>
        </div>

        <transition-group name="card" tag="div" class="cards-grid" v-else>
          <div v-for="item in knowledgeBaseItems" :key="item.id" class="k-card">
            <div class="k-card-body">
              <div class="k-card-header">
                <div class="k-card-title-row">
                  <h4 class="k-card-title">{{ item.title }}</h4>
                  <span
                    v-if="item.category"
                    class="k-card-tag"
                    :style="{ background: getCategoryColor(item.category) + '20', color: getCategoryColor(item.category), borderColor: getCategoryColor(item.category) + '40' }"
                  >
                    {{ item.category }}
                  </span>
                </div>
                <p class="k-card-preview">{{ previewContent(item.content) }}</p>
              </div>
              <div class="k-card-footer">
                <span class="k-card-date">{{ item.updated_at ? new Date(item.updated_at).toLocaleDateString('zh-CN') : '' }}</span>
                <button class="btn-delete" @click="confirmDelete(item.id)">
                  <span>🗑</span> 删除
                </button>
              </div>
            </div>
          </div>
        </transition-group>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <transition name="fade">
      <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="cancelDelete">
        <div class="modal-box">
          <div class="modal-icon">⚠️</div>
          <h3>确认删除</h3>
          <p>删除后该知识将从向量库中移除，无法恢复。</p>
          <div class="modal-actions">
            <button class="btn-modal-cancel" @click="cancelDelete">取消</button>
            <button class="btn-modal-confirm" @click="executeDelete">确认删除</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
/* ===== 页面基础 ===== */
.kb-page {
  min-height: 100vh;
  background: #020617;
  position: relative;
  overflow-x: hidden;
  color: #e2e8f0;
}

/* ===== 装饰性背景 ===== */
.decorative-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.bg-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
}

.bg-blob-1 {
  top: -10%;
  left: -10%;
  width: 50%;
  height: 50%;
  background: rgba(99, 102, 241, 0.15);
}

.bg-blob-2 {
  bottom: -10%;
  right: -10%;
  width: 40%;
  height: 40%;
  background: rgba(147, 51, 234, 0.12);
}

.grid-bg {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  opacity: 0.06;
  background-image: radial-gradient(#1e293b 1px, transparent 1px);
  background-size: 40px 40px;
}

/* ===== 容器 ===== */
.kb-container {
  position: relative;
  z-index: 1;
  max-width: 1000px;
  margin: 0 auto;
  padding: 32px 24px 60px;
}

/* ===== Header ===== */
.kb-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
  flex-wrap: wrap;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.logo-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  box-shadow: 0 0 24px rgba(79, 70, 229, 0.35);
}

.kb-title {
  font-size: 26px;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 4px;
  letter-spacing: -0.5px;
}

.kb-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  font-size: 13px;
  color: #94a3b8;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: #22d3ee;
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(34, 211, 238, 0.5);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 4px 16px rgba(79, 70, 229, 0.3);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(79, 70, 229, 0.4);
}

.btn-icon {
  font-size: 16px;
  font-weight: 700;
}

/* ===== 搜索区 ===== */
.search-section {
  margin-bottom: 24px;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px;
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  transition: all 0.3s ease;
}

.search-box:focus-within {
  border-color: rgba(99, 102, 241, 0.5);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15), 0 0 24px rgba(79, 70, 229, 0.1);
}

.search-icon {
  margin-left: 14px;
  font-size: 18px;
  opacity: 0.6;
}

.search-input {
  flex: 1;
  padding: 12px 8px;
  background: transparent;
  border: none;
  color: #ffffff;
  font-size: 15px;
  outline: none;
}

.search-input::placeholder {
  color: #475569;
}

.search-btn {
  padding: 10px 22px;
  background: rgba(79, 70, 229, 0.9);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.search-btn:hover:not(:disabled) {
  background: #4f46e5;
  transform: translateY(-1px);
}

.search-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.search-tip {
  font-size: 13px;
  color: #64748b;
  margin: 10px 0 0 16px;
}

.clear-link {
  color: #4f46e5;
  margin-left: 8px;
  text-decoration: none;
}

.clear-link:hover {
  text-decoration: underline;
}

/* ===== 搜索结果 ===== */
.results-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 28px;
}

.result-card {
  position: relative;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.result-card:hover {
  border-color: rgba(99, 102, 241, 0.25);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.result-glow {
  position: absolute;
  top: 0;
  left: 0;
  width: 3px;
  height: 100%;
  background: linear-gradient(180deg, #4f46e5 0%, #22d3ee 100%);
  opacity: 0.8;
}

.result-body {
  padding: 18px 20px 18px 24px;
}

.result-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  flex-wrap: wrap;
  gap: 8px;
}

.result-title {
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
}

.similarity-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 120px;
}

.similarity-fill {
  height: 4px;
  background: linear-gradient(90deg, #4f46e5, #22d3ee);
  border-radius: 2px;
  transition: width 0.6s ease;
}

.similarity-text {
  font-size: 12px;
  color: #22d3ee;
  font-weight: 600;
  white-space: nowrap;
}

.result-text {
  font-size: 13.5px;
  color: #94a3b8;
  line-height: 1.7;
  margin: 0 0 10px;
}

.result-meta {
  display: flex;
  gap: 8px;
}

.meta-tag {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

/* ===== 添加面板 ===== */
.add-panel {
  position: relative;
  margin-bottom: 32px;
  border-radius: 20px;
  overflow: hidden;
}

.panel-glow {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.15) 0%, rgba(124, 58, 237, 0.1) 100%);
  border-radius: 20px;
  filter: blur(20px);
  z-index: 0;
}

.add-panel-inner {
  position: relative;
  z-index: 1;
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 24px;
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 20px;
}

.add-grid {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 24px;
}

@media (max-width: 768px) {
  .add-grid {
    grid-template-columns: 1fr;
  }
}

.add-col {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-label {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}

.field-input,
.field-textarea {
  padding: 12px 14px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  color: #e2e8f0;
  font-size: 14px;
  outline: none;
  transition: all 0.2s ease;
}

.field-input:focus,
.field-textarea:focus {
  border-color: rgba(99, 102, 241, 0.4);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.field-input::placeholder,
.field-textarea::placeholder {
  color: #475569;
}

.field-textarea {
  resize: vertical;
  min-height: 100px;
  line-height: 1.6;
}

.btn-submit {
  margin-top: 4px;
  padding: 12px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.25);
}

.btn-submit:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.35);
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ===== 上传卡片 ===== */
.upload-col {
  justify-content: center;
}

.upload-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 28px 20px;
  background: rgba(15, 23, 42, 0.5);
  border: 2px dashed rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  text-align: center;
  transition: all 0.3s ease;
}

.upload-card:hover {
  border-color: rgba(99, 102, 241, 0.3);
  background: rgba(15, 23, 42, 0.6);
}

.upload-icon {
  font-size: 36px;
  margin-bottom: 4px;
}

.upload-card h4 {
  font-size: 15px;
  color: #ffffff;
  margin: 0;
}

.upload-desc {
  font-size: 12px;
  color: #64748b;
  margin: 0;
}

.hidden-input {
  display: none;
}

.btn-upload {
  padding: 10px 24px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.25);
}

.btn-upload:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.35);
}

.upload-limit {
  font-size: 11px;
  color: #475569;
  margin: 0;
}

.upload-error {
  font-size: 12px;
  color: #ef4444;
  margin: 0;
}

/* ===== 列表区 ===== */
.list-section {
  margin-top: 8px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.list-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0;
}

.list-count {
  font-size: 13px;
  color: #64748b;
  background: rgba(15, 23, 42, 0.6);
  padding: 4px 12px;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

/* ===== 卡片网格 ===== */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.k-card {
  position: relative;
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.k-card:hover {
  border-color: rgba(99, 102, 241, 0.2);
  transform: translateY(-4px) scale(1.01);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(79, 70, 229, 0.1);
}

.k-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 16px;
  padding: 1.5px;
  background: linear-gradient(135deg, #4f46e5, #7c3aed, #22d3ee, #ec4899, #f59e0b, #4f46e5);
  background-size: 300% 300%;
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0;
  transition: opacity 0.4s ease;
  pointer-events: none;
  animation: rainbow-shift 4s linear infinite;
}

.k-card:hover::before {
  opacity: 1;
}

@keyframes rainbow-shift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.k-card-body {
  padding: 18px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.k-card-header {
  flex: 1;
}

.k-card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;
}

.k-card-title {
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
  line-height: 1.4;
}

.k-card-tag {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 20px;
  border: 1px solid;
  white-space: nowrap;
  flex-shrink: 0;
}

.k-card-preview {
  font-size: 13px;
  color: #64748b;
  line-height: 1.6;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.k-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
}

.k-card-date {
  font-size: 11px;
  color: #475569;
}

.btn-delete {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 8px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-delete:hover {
  background: rgba(239, 68, 68, 0.2);
  transform: scale(1.05);
}

/* ===== 空状态 / 加载状态 ===== */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #475569;
  text-align: center;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(79, 70, 229, 0.2);
  border-top-color: #4f46e5;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.6;
}

.empty-state h4 {
  font-size: 16px;
  color: #94a3b8;
  margin: 0 0 6px;
}

.empty-state p {
  font-size: 13px;
  color: #475569;
  margin: 0;
}

/* ===== 删除确认弹窗 ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.8);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-box {
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 32px;
  text-align: center;
  max-width: 360px;
  width: 90%;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5);
}

.modal-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.modal-box h3 {
  font-size: 18px;
  color: #ffffff;
  margin: 0 0 8px;
}

.modal-box p {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 24px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn-modal-cancel {
  padding: 10px 20px;
  background: transparent;
  color: #94a3b8;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-modal-cancel:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #e2e8f0;
}

.btn-modal-confirm {
  padding: 10px 20px;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 16px rgba(239, 68, 68, 0.25);
}

.btn-modal-confirm:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(239, 68, 68, 0.35);
}

/* ===== 动画 ===== */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
  margin-bottom: 0;
  transform: translateY(-10px);
}

.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 800px;
  transform: translateY(0);
}

.fade-up-enter-active,
.fade-up-leave-active {
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-up-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.fade-up-enter-to {
  opacity: 1;
  transform: translateY(0);
}

.card-enter-active,
.card-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.card-enter-from {
  opacity: 0;
  transform: scale(0.95) translateY(10px);
}

.card-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
