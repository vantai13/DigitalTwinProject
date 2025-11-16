<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { io } from 'socket.io-client'

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

// ✅ SỬA LỖI: Khai báo socket NGOÀI onMounted
let socket = null

// ============================================
// API FUNCTIONS
// ============================================
const API_BASE_URL = 'http://localhost:5000/api'
const SOCKET_URL = 'http://localhost:5000'

async function checkBackendHealth() {
  try {
    const response = await axios.get(`${API_BASE_URL}/health`, {
      timeout: 2000
    })
    console.log('✅ Backend health:', response.data)
    return true
  } catch (error) {
    console.error('❌ Backend không phản hồi:', error.message)
    return false
  }
}

function retryConnection() {
  retryCount.value = 0
  errorMessage.value = null
  connectionStatus.value = 'connecting'
  isLoading.value = true
  
  // ✅ Reconnect socket
  if (socket) {
    socket.disconnect()
    socket.connect()
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
// WEBSOCKET SETUP
// ============================================
function setupWebSocket() {
  console.log('🔌 Đang kết nối WebSocket...')
  
  socket = io(SOCKET_URL, {
    transports: ['websocket', 'polling'],  // ✅ Thử websocket trước
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 5
  })

  // 1. ✅ Nhận trạng thái ban đầu
  socket.on('initial_state', (data) => {
    console.log('✅ Nhận initial_state từ Backend')
    networkData.value = data
    isLoading.value = false
    connectionStatus.value = 'connected'
    errorMessage.value = null
  })

  // 2. ✅ Lắng nghe cập nhật Host
  socket.on('host_updated', (updatedHost) => {
    if (!networkData.value) return
    console.log('🔄 Host updated:', updatedHost.name)

    const index = networkData.value.graph_data.nodes.findIndex(
      n => n.id === updatedHost.name && n.group.startsWith('host')
    )
    
    if (index !== -1) {
      const oldNode = networkData.value.graph_data.nodes[index]
      networkData.value.graph_data.nodes[index] = {
        ...oldNode,
        details: updatedHost
      }
    }
  })

  // 3. ✅ Lắng nghe cập nhật Switch
  socket.on('switch_updated', (updatedSwitch) => {
    if (!networkData.value) return
    console.log('🔄 Switch updated:', updatedSwitch.name)

    const index = networkData.value.graph_data.nodes.findIndex(
      n => n.id === updatedSwitch.name && n.group.startsWith('switch')
    )
    
    if (index !== -1) {
      const oldNode = networkData.value.graph_data.nodes[index]
      networkData.value.graph_data.nodes[index] = {
        ...oldNode,
        details: updatedSwitch
      }
    }
  })

  // 4. ✅ Lắng nghe cập nhật Link
  socket.on('link_updated', (updatedLink) => {
    if (!networkData.value) return
    console.log('🔄 Link updated:', updatedLink.id)
    
    const index = networkData.value.graph_data.edges.findIndex(
      e => e.id === updatedLink.id
    )
    
    if (index !== -1) {
      const oldEdge = networkData.value.graph_data.edges[index]
      networkData.value.graph_data.edges[index] = {
        ...oldEdge,
        label: `${updatedLink.current_throughput.toFixed(1)} Mbps`,
        utilization: updatedLink.utilization,
        status: updatedLink.status,
        details: updatedLink
      }
    }
  })
  
  // 5. ✅ Xử lý kết nối thành công
  socket.on('connect', () => {
    console.log('✅ WebSocket connected!')
    connectionStatus.value = 'connected'
    errorMessage.value = null
  })

  // 6. ✅ Xử lý mất kết nối
  socket.on('disconnect', (reason) => {
    console.warn('❌ WebSocket disconnected:', reason)
    connectionStatus.value = 'error'
    errorMessage.value = '🔌 Mất kết nối tới máy chủ real-time.'
  })

  // 7. ✅ Xử lý lỗi kết nối
  socket.on('connect_error', (error) => {
    console.error('❌ WebSocket error:', error.message)
    connectionStatus.value = 'error'
    errorMessage.value = `🔴 Không thể kết nối WebSocket: ${error.message}`
    isLoading.value = false
  })
}

// ============================================
// LIFECYCLE
// ============================================
onMounted(async () => {
  console.log('🚀 Frontend đang khởi động...')
  
  const isHealthy = await checkBackendHealth()
  
  if (!isHealthy) {
    errorMessage.value = "🔴 Backend Flask chưa chạy hoặc chưa sẵn sàng"
    connectionStatus.value = 'error'
    isLoading.value = false
    return
  }

  // ✅ Khởi tạo WebSocket
  setupWebSocket()
})

onUnmounted(() => {
  if (socket) {
    console.log('🔌 Đang ngắt kết nối WebSocket...')
    socket.disconnect()
  }
})
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
/* (Giữ nguyên CSS như cũ) */
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