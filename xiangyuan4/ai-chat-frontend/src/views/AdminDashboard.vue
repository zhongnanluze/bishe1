<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { apiService } from '../services/apiService'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

const props = defineProps({
  activeTab: { type: String, default: 'overview' }
})

const loading = ref(true)
const overview = ref({ total_calls: 0, total_tokens: 0, active_users: 0, total_users: 0, today_calls: 0, today_tokens: 0 })
const userStats = ref([])
const agentStats = ref([])
const trendData = ref({ dates: [], call_counts: [], token_counts: [] })
const agentTrendData = ref({ dates: [], agents: [] })

// 智能体名称映射
const agentNameMap = {
  academic: '学生学业',
  student_services: '学生办事',
  psychology: '心理咨询',
  policy: '制度查询',
  chat: '日常聊天'
}

const agentColors = {
  academic: '#a78bfa',
  student_services: '#f472b6',
  psychology: '#fb923c',
  policy: '#fbbf24',
  chat: '#22d3ee'
}

// 概览卡片数据
const overviewCards = computed(() => [
  { label: '总调用次数', value: overview.value.total_calls, icon: '📞', color: '#4f46e5' },
  { label: '总Token用量', value: overview.value.total_tokens.toLocaleString(), icon: '🔤', color: '#22d3ee' },
  { label: '活跃用户', value: overview.value.active_users, icon: '👤', color: '#f472b6' },
  { label: '今日调用', value: overview.value.today_calls, icon: '📅', color: '#34d399' }
])

// 折线图：调用趋势
const trendLineOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
  legend: { data: ['调用次数', 'Token用量'], textStyle: { color: '#94a3b8' }, bottom: 0 },
  grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: trendData.value.dates,
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
    axisLabel: { color: '#64748b', fontSize: 11 }
  },
  yAxis: [
    { type: 'value', name: '调用次数', axisLine: { show: false }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }, axisLabel: { color: '#64748b' } },
    { type: 'value', name: 'Token', axisLine: { show: false }, splitLine: { show: false }, axisLabel: { color: '#64748b' } }
  ],
  series: [
    { name: '调用次数', type: 'line', smooth: true, data: trendData.value.call_counts, itemStyle: { color: '#4f46e5' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(79,70,229,0.3)' }, { offset: 1, color: 'rgba(79,70,229,0)' }] } } },
    { name: 'Token用量', type: 'line', smooth: true, yAxisIndex: 1, data: trendData.value.token_counts, itemStyle: { color: '#22d3ee' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(34,211,238,0.3)' }, { offset: 1, color: 'rgba(34,211,238,0)' }] } } }
  ]
}))

// 饼图：智能体占比
const agentPieOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { orient: 'vertical', right: '5%', top: 'center', textStyle: { color: '#94a3b8' } },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    center: ['40%', '50%'],
    avoidLabelOverlap: false,
    itemStyle: { borderRadius: 8, borderColor: '#020617', borderWidth: 2 },
    label: { show: false },
    emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#fff' } },
    data: agentStats.value.map(a => ({
      value: a.call_count,
      name: agentNameMap[a.agent_type] || a.agent_type,
      itemStyle: { color: agentColors[a.agent_type] || '#64748b' }
    }))
  }]
}))

// 柱状图：用户Token用量TOP10
const userBarOption = computed(() => {
  const topUsers = userStats.value.slice(0, 10)
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: topUsers.map(u => u.full_name || u.username),
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#64748b', fontSize: 11, rotate: 30 }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      axisLabel: { color: '#64748b' }
    },
    series: [{
      type: 'bar',
      data: topUsers.map(u => u.total_tokens),
      itemStyle: {
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#7c3aed' }, { offset: 1, color: '#4f46e5' }] },
        borderRadius: [6, 6, 0, 0]
      },
      barWidth: '50%'
    }]
  }
})

// 堆叠柱状图：各智能体每日趋势
const agentStackOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  legend: { textStyle: { color: '#94a3b8' }, bottom: 0 },
  grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
  xAxis: {
    type: 'category',
    data: agentTrendData.value.dates,
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
    axisLabel: { color: '#64748b', fontSize: 11 }
  },
  yAxis: {
    type: 'value',
    axisLine: { show: false },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
    axisLabel: { color: '#64748b' }
  },
  series: agentTrendData.value.agents.map(a => ({
    name: agentNameMap[a.agent_type] || a.agent_type,
    type: 'bar',
    stack: 'total',
    data: a.call_counts,
    itemStyle: { color: agentColors[a.agent_type] || '#64748b', borderRadius: [0, 0, 0, 0] }
  }))
}))

const fetchData = async () => {
  loading.value = true
  try {
    const [ov, us, ag, tr, at] = await Promise.all([
      apiService.get('/admin/stats/overview'),
      apiService.get('/admin/stats/by-user?days=30'),
      apiService.get('/admin/stats/by-agent?days=30'),
      apiService.get('/admin/stats/trend?days=14'),
      apiService.get('/admin/stats/agent-trend?days=14')
    ])
    overview.value = ov
    userStats.value = us.users || []
    agentStats.value = ag.agents || []
    trendData.value = tr
    agentTrendData.value = at
  } catch (error) {
    console.error('获取统计数据失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})

watch(() => props.activeTab, () => {
  // 切换标签时重新获取数据
  fetchData()
})
</script>

<template>
  <div class="dashboard-page">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <p>加载统计数据...</p>
    </div>

    <template v-else>
      <!-- 概览卡片 -->
      <div class="overview-cards" v-if="activeTab === 'overview' || activeTab === 'users' || activeTab === 'agents'">
        <div v-for="card in overviewCards" :key="card.label" class="overview-card">
          <div class="card-icon" :style="{ background: card.color + '20', color: card.color }">
            {{ card.icon }}
          </div>
          <div class="card-info">
            <p class="card-value">{{ card.value }}</p>
            <p class="card-label">{{ card.label }}</p>
          </div>
        </div>
      </div>

      <!-- 图表区域 -->
      <div class="charts-grid">
        <!-- 调用趋势折线图 -->
        <div class="chart-card" v-if="activeTab === 'overview' || activeTab === 'agents'">
          <div class="chart-header">
            <h4>📈 调用趋势（最近14天）</h4>
          </div>
          <v-chart class="chart" :option="trendLineOption" autoresize />
        </div>

        <!-- 智能体占比饼图 -->
        <div class="chart-card" v-if="activeTab === 'overview' || activeTab === 'agents'">
          <div class="chart-header">
            <h4>🥧 智能体调用占比</h4>
          </div>
          <v-chart class="chart" :option="agentPieOption" autoresize />
        </div>

        <!-- 用户Token用量柱状图 -->
        <div class="chart-card" v-if="activeTab === 'overview' || activeTab === 'users'">
          <div class="chart-header">
            <h4>📊 用户Token用量TOP10</h4>
          </div>
          <v-chart class="chart" :option="userBarOption" autoresize />
        </div>

        <!-- 智能体每日趋势堆叠图 -->
        <div class="chart-card" v-if="activeTab === 'overview' || activeTab === 'agents'">
          <div class="chart-header">
            <h4>📉 各智能体每日调用趋势</h4>
          </div>
          <v-chart class="chart" :option="agentStackOption" autoresize />
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.dashboard-page {
  max-width: 1200px;
  margin: 0 auto;
}

/* 加载 */
.loading-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px;
  color: #64748b;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(79, 70, 229, 0.2);
  border-top-color: #4f46e5;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 概览卡片 */
.overview-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.overview-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.7) 0%, rgba(30, 41, 59, 0.5) 100%);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  backdrop-filter: blur(16px) saturate(1.2);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.overview-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 16px;
  padding: 1px;
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.2), rgba(124, 58, 237, 0.2), rgba(79, 70, 229, 0.2));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0;
  transition: opacity 0.4s ease;
  pointer-events: none;
}

.overview-card:hover::before {
  opacity: 1;
}

.overview-card:hover {
  border-color: rgba(255, 255, 255, 0.15);
  transform: translateY(-4px);
  box-shadow: 
    0 12px 40px rgba(0, 0, 0, 0.3),
    0 0 30px rgba(79, 70, 229, 0.1);
}

.card-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
  box-shadow: 
    0 4px 12px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
}

.card-value {
  font-size: 26px;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
  line-height: 1.2;
  text-shadow: 0 0 20px rgba(255, 255, 255, 0.15);
}

.card-label {
  font-size: 13px;
  color: #64748b;
  margin: 4px 0 0;
}

/* 图表网格 */
.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
  gap: 20px;
}

.chart-card {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.7) 0%, rgba(30, 41, 59, 0.5) 100%);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  padding: 20px;
  backdrop-filter: blur(16px) saturate(1.2);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.chart-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 16px;
  padding: 1px;
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.15), rgba(124, 58, 237, 0.15));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0;
  transition: opacity 0.4s ease;
  pointer-events: none;
}

.chart-card:hover::before {
  opacity: 1;
}

.chart-card:hover {
  border-color: rgba(255, 255, 255, 0.12);
  box-shadow: 
    0 8px 30px rgba(0, 0, 0, 0.3),
    0 0 30px rgba(79, 70, 229, 0.08);
}

.chart-header {
  margin-bottom: 12px;
}

.chart-header h4 {
  font-size: 14px;
  font-weight: 600;
  color: #f1f5f9;
  margin: 0;
  text-shadow: 0 0 10px rgba(34, 211, 238, 0.2);
}

.chart {
  width: 100%;
  height: 320px;
}

/* 响应式 */
@media (max-width: 768px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
  .chart {
    height: 260px;
  }
}
</style>
