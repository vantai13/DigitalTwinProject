<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { io } from 'socket.io-client'

import Header from './components/Header.vue'
import TopologyView from './components/TopologyView.vue'
import InfoPanel from './components/InfoPanel.vue'

// ============================================
// 1. CONFIGURATION (ENV VARIABLES)
// ============================================
// Tự động lấy từ file .env hoặc dùng mặc định nếu đang dev
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'
const SOCKET_URL = import.meta.env.VITE_SOCKET_URL || 'http://localhost:5000'

// ============================================
// 2. STATE MANAGEMENT
// ============================================
const networkData = ref(null)
const isLoading = ref(true)
const errorMessage = ref(null)
const selectedNodeId = ref(null)
const selectedEdgeId = ref(null)
const connectionStatus = ref('connecting') 

// Retry Logic
const retryCount = ref(0)
const MAX_RETRIES = 3
let retryTimer = null

// Socket Instance (Khai báo ở phạm vi Module để truy cập toàn cục trong file)
let socket = null

// Batch Update Queue (Hàng đợi cập nhật)
let updateQueue = []
let updateTimer = null

// ============================================
// 3. HELPER FUNCTIONS
// ============================================

async function checkBackendHealth() {
  try {
    const response = await axios.get(`${API_BASE_URL}/health`, { timeout: 2000 })
    console.log('Backend health:', response.data)
    return true
  } catch (error) {
    console.error(' Backend check failed:', error.message)
    return false
  }
}

// Hàm xử lý Batch Update (Tư duy người bồi bàn)
function processUpdateQueue() {
  if (!networkData.value || updateQueue.length === 0) return

  // Lặp qua hàng đợi và cập nhật dữ liệu
  // Việc này diễn ra rất nhanh trong bộ nhớ JS
  updateQueue.forEach(item => {
    const { type, data } = item
    
    if (type === 'node') {
      // Tìm và cập nhật Node (Host/Switch)
      const index = networkData.value.graph_data.nodes.findIndex(n => n.id === data.name)
      if (index !== -1) {
        // Giữ nguyên vị trí cũ, chỉ update details
        const oldNode = networkData.value.graph_data.nodes[index]
        networkData.value.graph_data.nodes[index] = { ...oldNode, details: data }
      }
    } else if (type === 'link') {
      // Tìm và cập nhật Link
      const index = networkData.value.graph_data.edges.findIndex(e => e.id === data.id)
      if (index !== -1) {
        const oldEdge = networkData.value.graph_data.edges[index]
        networkData.value.graph_data.edges[index] = {
          ...oldEdge,
          label: `${data.current_throughput.toFixed(1)} Mbps`,
          utilization: data.utilization,
          status: data.status,
          details: data
        }
      }
    }
  })

  // Dọn sạch hàng đợi
  updateQueue = []
  // Vue sẽ tự động gom các thay đổi trong networkData thành 1 lần re-render DOM
}

// Hàm helper để đẩy vào hàng đợi
function queueUpdate(type, data) {
  updateQueue.push({ type, data })
  
  // Reset timer cũ
  if (updateTimer) clearTimeout(updateTimer)
  
  // Đợi 50ms, nếu không có gì thêm mới chạy processUpdateQueue
  updateTimer = setTimeout(processUpdateQueue, 50)
}

function retryConnection() {
  retryCount.value = 0
  errorMessage.value = null
  connectionStatus.value = 'connecting'
  isLoading.value = true
  
  if (socket) {
    socket.connect()
  } else {
    setupWebSocket()
  }
}

// ============================================
// 4. WEBSOCKET SETUP
// ============================================
function setupWebSocket() {
  if (socket) return // Tránh tạo trùng lặp

  console.log(`🔌 Connecting to WebSocket at ${SOCKET_URL}...`)
  
  socket = io(SOCKET_URL, {
    transports: ['websocket', 'polling'],
    reconnection: false // Tắt tự động reconnect của lib để tự quản lý logic
  })

  socket.on('connect', () => {
    console.log(' WebSocket Connected!')
    connectionStatus.value = 'connected'
    errorMessage.value = null
    retryCount.value = 0
  })

  socket.on('initial_state', (data) => {
    networkData.value = data
    isLoading.value = false
  })

  // --- SỬ DỤNG BATCH UPDATE CHO CÁC SỰ KIỆN ---
  socket.on('host_updated', (updatedHost) => {
    queueUpdate('node', updatedHost)
  })

  socket.on('switch_updated', (updatedSwitch) => {
    queueUpdate('node', updatedSwitch)
  })

  socket.on('link_updated', (updatedLink) => {
    queueUpdate('link', updatedLink)
  })

  // --- XỬ LÝ LỖI VÀ RETRY ---
  socket.on('connect_error', (error) => {
    console.error('❌ Connection Error:', error.message)
    connectionStatus.value = 'error'
    
    if (retryCount.value < MAX_RETRIES) {
      const waitTime = 2000
      retryCount.value++
      errorMessage.value = `Connection lost. Retrying (${retryCount.value}/${MAX_RETRIES})...`
      
      console.log(`⏳ Waiting ${waitTime}ms before retry...`)
      if (retryTimer) clearTimeout(retryTimer)
      
      retryTimer = setTimeout(() => {
        if (socket) socket.connect()
      }, waitTime)
      
    } else {
      errorMessage.value = " Unable to connect to Backend. Please check if the server is running."
      isLoading.value = false
    }
  })
  
  socket.on('disconnect', (reason) => {
    if (reason === 'io server disconnect') {
      // Disconnect do server đá -> cần connect lại thủ công
      socket.connect();
    }
    connectionStatus.value = 'error'
  })
}

// ============================================
// 5. LIFECYCLE HOOKS
// ============================================
onMounted(async () => {
  // Check Health trước khi connect socket
  const isHealthy = await checkBackendHealth()
  if (!isHealthy) {
    errorMessage.value = "Backend is not reachable."
    connectionStatus.value = 'error'
    isLoading.value = false
    return
  }
  
  setupWebSocket()
})

onUnmounted(() => {
  // Dọn dẹp sạch sẽ khi thoát
  if (socket) {
    console.log(' Disconnecting socket...')
    socket.disconnect()
    socket = null
  }
  if (updateTimer) clearTimeout(updateTimer)
  if (retryTimer) clearTimeout(retryTimer)
})

// Events từ Component con
function handleNodeSelected(nodeId) {
  selectedNodeId.value = nodeId; selectedEdgeId.value = null
}
function handleEdgeSelected(edgeId) {
  selectedEdgeId.value = edgeId; selectedNodeId.value = null
}
function handleSelectionCleared() {
  selectedNodeId.value = null; selectedEdgeId.value = null
}
</script>

<template>
  <div class="app-container">
    <Header />

    <!-- MAIN CONTENT -->
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

    <!-- LOADING STATE -->
    <div v-if="isLoading && connectionStatus !== 'error'" class="loading-container">
      <div class="loading-spinner"></div>
      <p>Đang kết nối đến Backend Flask...</p>
    </div>

    <!-- ERROR STATE -->
    <div v-if="errorMessage && connectionStatus === 'error'" class="error-container">
      <div class="error-icon"><img src="./assets/icons/alert-triangle.svg" alt=""></div>
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
         Thử lại
      </button>
    </div>

    <!-- CONNECTION STATUS INDICATOR -->
    <div class="status-indicator" :class="connectionStatus">
      <span class="status-dot"></span>
      <span v-if="connectionStatus === 'connected'">Đã kết nối</span>
      <span v-else-if="connectionStatus === 'connecting'">Đang kết nối...</span>
      <span v-else>Mất kết nối</span>
    </div>
  </div>
</template>
<style>

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