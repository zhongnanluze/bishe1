import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'
import VChart from 'vue-echarts'

const app = createApp(App)
app.use(router)
app.component('v-chart', VChart)
app.mount('#app')
