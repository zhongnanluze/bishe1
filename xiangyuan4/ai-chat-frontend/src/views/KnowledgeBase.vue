<script setup>
import { ref, onMounted } from 'vue'
import { apiService } from '../services/apiService'

const knowledgeBaseItems = ref([])
const isLoading = ref(false)
const isAdding = ref(false)
const newItem = ref({
  title: '',
  content: '',
  category: ''
})
const showAddForm = ref(false)

// 加载知识库数据
const loadKnowledgeBase = async () => {
  isLoading.value = true
  try {
    const response = await apiService.getKnowledgeBase()
    knowledgeBaseItems.value = response.data
  } catch (error) {
    console.error('加载知识库失败:', error)
  } finally {
    isLoading.value = false
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
  } catch (error) {
    console.error('添加知识库项失败:', error)
  } finally {
    isAdding.value = false
  }
}

// 删除知识库项
const deleteKnowledgeBaseItem = async (id) => {
  if (!confirm('确定要删除这个知识库项吗？')) {
    return
  }
  
  try {
    await apiService.deleteKnowledgeBaseItem(id)
    await loadKnowledgeBase()
  } catch (error) {
    console.error('删除知识库项失败:', error)
  }
}

onMounted(() => {
  loadKnowledgeBase()
})
</script>

<template>
  <div class="knowledge-base-container">
    <header class="page-header">
      <h1>知识库维护</h1>
      <button class="add-btn" @click="showAddForm = !showAddForm">
        {{ showAddForm ? '取消' : '添加知识' }}
      </button>
    </header>
    
    <!-- 添加表单 -->
    <div v-if="showAddForm" class="add-form">
      <div class="form-group">
        <label>标题</label>
        <input v-model="newItem.title" type="text" placeholder="请输入知识标题" />
      </div>
      <div class="form-group">
        <label>分类</label>
        <input v-model="newItem.category" type="text" placeholder="请输入分类" />
      </div>
      <div class="form-group">
        <label>内容</label>
        <textarea v-model="newItem.content" placeholder="请输入知识内容" rows="4"></textarea>
      </div>
      <button class="submit-btn" @click="addKnowledgeBaseItem" :disabled="isAdding">
        {{ isAdding ? '添加中...' : '添加' }}
      </button>
    </div>
    
    <!-- 知识库列表 -->
    <div class="knowledge-base-list">
      <div v-if="isLoading" class="loading">加载中...</div>
      <div v-else-if="knowledgeBaseItems.length === 0" class="empty">暂无知识库数据</div>
      <div v-else class="items">
        <div v-for="item in knowledgeBaseItems" :key="item.id" class="knowledge-item">
          <div class="item-header">
            <h3>{{ item.title }}</h3>
            <span class="category">{{ item.category || '未分类' }}</span>
          </div>
          <div class="item-content">{{ item.content }}</div>
          <div class="item-actions">
            <button class="delete-btn" @click="deleteKnowledgeBaseItem(item.id)">删除</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.knowledge-base-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  font-size: 24px;
  color: #ffffff;
}

.add-btn {
  background-color: #4f46e5;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s;
}

.add-btn:hover {
  background-color: #4338ca;
}

.add-form {
  background-color: rgba(15, 23, 42, 0.6);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  border: 1px solid rgba(30, 41, 59, 0.5);
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-size: 14px;
  color: #94a3b8;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  background-color: rgba(15, 23, 42, 0.8);
  color: #ffffff;
  font-size: 14px;
}

.form-group textarea {
  resize: vertical;
}

.submit-btn {
  background-color: #10b981;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s;
}

.submit-btn:hover {
  background-color: #059669;
}

.submit-btn:disabled {
  background-color: #6b7280;
  cursor: not-allowed;
}

.knowledge-base-list {
  min-height: 400px;
}

.loading,
.empty {
  text-align: center;
  padding: 40px 0;
  color: #94a3b8;
}

.items {
  display: grid;
  gap: 16px;
}

.knowledge-item {
  background-color: rgba(15, 23, 42, 0.6);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid rgba(30, 41, 59, 0.5);
  transition: transform 0.2s, box-shadow 0.2s;
}

.knowledge-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.item-header h3 {
  font-size: 16px;
  color: #ffffff;
  margin: 0;
}

.category {
  font-size: 12px;
  color: #94a3b8;
  background-color: rgba(30, 41, 59, 0.5);
  padding: 2px 8px;
  border-radius: 12px;
}

.item-content {
  font-size: 14px;
  color: #e2e8f0;
  margin-bottom: 12px;
  line-height: 1.5;
}

.item-actions {
  display: flex;
  justify-content: flex-end;
}

.delete-btn {
  background-color: #ef4444;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: background-color 0.2s;
}

.delete-btn:hover {
  background-color: #dc2626;
}
</style>