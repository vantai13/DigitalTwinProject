<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

import Header from './components/Header.vue'
import TopologyView from './components/TopologyView.vue'
import InfoPanel from './components/InfoPanel.vue'

// ============================================
// STATE MANAGEMENT
// ============================================
const networkData = ref(null)
const isLoading = ref(true)
const errorMessage = ref(null)
const selectedNodeId = ref(null)
const selectedEdgeId = ref(null)
const connectionStatus = ref('connecting') // 'connecting', 'connected', 'error'
const retryCount = ref(0)
const maxRetries = 3

let pollingInterval = null

// ============================================
// API FUNCTIONS
// ============================================
const API_BASE_URL = 'http://localhost:5000/api'

async function fetchData() {
  try {
    const response = await axios.get(`${API_BASE_URL}/network/status`, {
      timeout: 5000 // 5s timeout
    })
    
    networkData.value = response.data
    errorMessage.value = null
    connectionStatus.value = 'connected'
    retryCount.value = 0 // Reset retry count on success
    
  } catch (error) {
    console.error(" Lỗi khi gọi API:", error)
    
    if (error.code === 'ECONNABORTED') {
      errorMessage.value = "⏱️ Timeout: Backend phản hồi quá chậm"
    } else if (error.code === 'ERR_NETWORK') {
      errorMessage.value = "🔌 Không thể kết nối đến Backend Flask"
    } else if (error.response) {
      errorMessage.value = `❌ Backend trả về lỗi ${error.response.status}`
    } else {
      errorMessage.value = "❓ Lỗi không xác định"
    }
    
    connectionStatus.value = 'error'
    retryCount.value++
    
    // Dừng polling nếu lỗi quá nhiều
    if (retryCount.value >= maxRetries && pollingInterval) {
      clearInterval(pollingInterval)
      console.warn(`⚠️ Đã dừng polling sau ${maxRetries} lần thất bại`)
    }
    
  } finally {
    isLoading.value = false
  }
}

// Health check để kiểm tra Backend có sống không
async function checkBackendHealth() {
  try {
    const response = await axios.get(`${API_BASE_URL}/health`, {
      timeout: 2000
    })
    console.log(' Backend health:', response.data)
    return true
  } catch (error) {
    console.error(' Backend không phản hồi:', error.message)
    return false
  }
}

// Manual retry
function retryConnection() {
  retryCount.value = 0
  errorMessage.value = null
  connectionStatus.value = 'connecting'
  isLoading.value = true
  
  fetchData()
  
  // Restart polling
  if (!pollingInterval) {
    pollingInterval = setInterval(fetchData, 2000)
  }
}

// ============================================
// EVENT HANDLERS
// ============================================
function handleNodeSelected(nodeId) {
  selectedNodeId.value = nodeId
  selectedEdgeId.value = null
}

function handleEdgeSelected(edgeId) {
  selectedEdgeId.value = edgeId
  selectedNodeId.value = null
}

function handleSelectionCleared() {
  selectedNodeId.value = null
  selectedEdgeId.value = null
}

// ============================================
// LIFECYCLE
// ============================================
onMounted(async () => {
  console.log('Frontend đang khởi động...')
  
  // Kiểm tra Backend trước
  const isHealthy = await checkBackendHealth()
  
  if (!isHealthy) {
    errorMessage.value = "🔴 Backend Flask chưa chạy hoặc chưa sẵn sàng"
    connectionStatus.value = 'error'
    isLoading.value = false
    return
  }
  
  // Fetch dữ liệu lần đầu
  await fetchData()
  
  // Bắt đầu polling (mỗi 2s)
  pollingInterval = setInterval(fetchData, 2000)
  console.log('✅ Polling đã bắt đầu (mỗi 2s)')
})

onUnmounted(() => {
  // Dọn dẹp khi component bị destroy
  if (pollingInterval) {
    clearInterval(pollingInterval)
    console.log('🧹 Đã dừng polling')
  }
})
</script>

<template>
  <div class="app-container">
    <Header />

    <!-- ============================================ -->
    <!-- MAIN CONTENT (Khi có dữ liệu) -->
    <!-- ============================================ -->
    <div v-if="networkData && connectionStatus === 'connected'" class="main-content">
      <TopologyView 
        :graphData="networkData.graph_data"
        @node-selected="handleNodeSelected"
        @edge-selected="handleEdgeSelected"
        @selection-cleared="handleSelectionCleared"
      />
      
      <InfoPanel
        :networkData="networkData"
        :selectedNodeId="selectedNodeId"
        :selectedEdgeId="selectedEdgeId"
      />
    </div>

    <!-- ============================================ -->
    <!-- LOADING STATE -->
    <!-- ============================================ -->
    <div v-if="isLoading && connectionStatus !== 'error'" class="loading-container">
      <div class="loading-spinner"></div>
      <p>Đang kết nối đến Backend Flask...</p>
    </div>

    <!-- ============================================ -->
    <!-- ERROR STATE -->
    <!-- ============================================ -->
    <div v-if="errorMessage && connectionStatus === 'error'" class="error-container">
      <div class="error-icon">⚠️</div>
      <h2>Không thể kết nối</h2>
      <p class="error-message">{{ errorMessage }}</p>
      
      <div class="error-details">
        <p><strong>Lần thử:</strong> {{ retryCount }} / {{ maxRetries }}</p>
        <p><strong>Hướng dẫn:</strong></p>
        <ul>
          <li>Kiểm tra Flask Backend đang chạy tại <code>localhost:5000</code></li>
          <li>Kiểm tra file <code>topology.json</code> tồn tại</li>
          <li>Xem log trong terminal Backend</li>
        </ul>
      </div>
      
      <button class="retry-button" @click="retryConnection">
        🔄 Thử lại
      </button>
    </div>

    <!-- ============================================ -->
    <!-- CONNECTION STATUS INDICATOR (Bottom) -->
    <!-- ============================================ -->
    <div class="status-indicator" :class="connectionStatus">
      <span class="status-dot"></span>
      <span v-if="connectionStatus === 'connected'">Đã kết nối</span>
      <span v-else-if="connectionStatus === 'connecting'">Đang kết nối...</span>
      <span v-else>Mất kết nối</span>
    </div>
  </div>
</template>

<style>
/* ============================================ */
/* GLOBAL STYLES */
/* ============================================ */
body, html {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: 'Arial', sans-serif; 
  background-color: #0f172a;
}

.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  position: relative;
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ============================================ */
/* LOADING STATE */
/* ============================================ */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: calc(100vh - 60px);
  color: #94a3b8;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #334155;
  border-top: 4px solid #00F7F7;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* ============================================ */
/* ERROR STATE */
/* ============================================ */
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: calc(100vh - 60px);
  color: #94a3b8;
  padding: 2rem;
  text-align: center;
}

.error-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.error-container h2 {
  color: #f87171;
  margin-bottom: 0.5rem;
}

.error-message {
  color: #fca5a5;
  font-size: 1.1rem;
  margin-bottom: 2rem;
}

.error-details {
  background-color: #1e293b;
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid #334155;
  max-width: 600px;
  text-align: left;
  margin-bottom: 2rem;
}

.error-details ul {
  margin: 0.5rem 0 0 1.5rem;
  color: #94a3b8;
}

.error-details code {
  background-color: #0f172a;
  padding: 2px 6px;
  border-radius: 4px;
  color: #00F7F7;
}

.retry-button {
  padding: 0.75rem 2rem;
  background-color: #00F7F7;
  color: #0f172a;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.retry-button:hover {
  background-color: #ffffff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 247, 247, 0.4);
}

/* ============================================ */
/* CONNECTION STATUS INDICATOR */
/* ============================================ */
.status-indicator {
  position: fixed;
  bottom: 20px;
  right: 20px;
  display: flex;
  align-items: center;
  padding: 0.75rem 1.25rem;
  background-color: rgba(30, 41, 59, 0.95);
  border-radius: 8px;
  border: 1px solid #334155;
  font-size: 0.9rem;
  font-weight: 500;
  z-index: 1000;
  backdrop-filter: blur(10px);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 0.5rem;
  animation: pulse 2s infinite;
}

.status-indicator.connected {
  border-color: #10b981;
  color: #10b981;
}

.status-indicator.connected .status-dot {
  background-color: #10b981;
}

.status-indicator.connecting {
  border-color: #f59e0b;
  color: #f59e0b;
}

.status-indicator.connecting .status-dot {
  background-color: #f59e0b;
}

.status-indicator.error {
  border-color: #ef4444;
  color: #ef4444;
}

.status-indicator.error .status-dot {
  background-color: #ef4444;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* ============================================ */
/* RESPONSIVE */
/* ============================================ */
@media (max-width: 768px) {
  .main-content {
    flex-direction: column;
  }
  
  .status-indicator {
    bottom: 10px;
    right: 10px;
    font-size: 0.8rem;
    padding: 0.5rem 0.75rem;
  }
}
</style>