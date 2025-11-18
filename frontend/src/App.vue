<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { io } from 'socket.io-client'

import Header from './components/Header.vue'
import TopologyView from './components/TopologyView.vue'
import InfoPanel from './components/InfoPanel.vue'

// ============================================
// 1. CONFIGURATION
// ============================================
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
const lastUpdateTime = ref(new Date().toISOString())

let socket = null

// ============================================
// 3. HELPER FUNCTIONS
// ============================================

async function checkBackendHealth() {
  try {
    const response = await axios.get(`${API_BASE_URL}/health`, { timeout: 2000 })
    console.log('✅ Backend health:', response.data)
    return true
  } catch (error) {
    console.error('❌ Backend check failed:', error.message)
    return false
  }
}

function retryConnection() {
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
// 4. WEBSOCKET SETUP (FIXED)
// ============================================
function setupWebSocket() {
  if (socket) return

  console.log(`🔌 Connecting to WebSocket at ${SOCKET_URL}...`)
  
  socket = io(SOCKET_URL, {
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000
  })

  socket.on('connect', () => {
    console.log('✅ WebSocket Connected!')
    connectionStatus.value = 'connected'
    errorMessage.value = null
  })

  // [FIXED] Nhận topology ban đầu
  socket.on('initial_state', (data) => {
    console.log('📦 Received initial topology:', data)
    networkData.value = data
    isLoading.value = false
    lastUpdateTime.value = new Date().toISOString()
  })

  // [FIXED] Xử lý batch update từ Mininet
  socket.on('network_batch_update', (batchData) => {
    if (!networkData.value) {
      console.warn('⚠️ NetworkData chưa khởi tạo, bỏ qua batch update')
      return
    }

    console.log('🔄 Processing batch update:', {
      hosts: batchData.hosts?.length || 0,
      links: batchData.links?.length || 0,
      switches: batchData.switches?.length || 0
    })

    // 1. Cập nhật Hosts
    if (batchData.hosts && Array.isArray(batchData.hosts)) {
      batchData.hosts.forEach(hData => {
        const nodeIndex = networkData.value.graph_data.nodes.findIndex(
          n => n.id === hData.name
        )
        
        if (nodeIndex !== -1) {
          const node = networkData.value.graph_data.nodes[nodeIndex]
          
          // Merge dữ liệu mới
          node.details = {
            ...node.details,
            cpu_utilization: hData.cpu,
            memory_usage: hData.mem,
            status: hData.cpu > 90 ? 'high-load' : 'up'
          }
          
          // Cập nhật group để đổi màu node
          if (hData.cpu > 90) {
            node.group = 'host-high-load'
          } else {
            node.group = 'host'
          }
        }
      })
    }

    // 2. Cập nhật Links
    if (batchData.links && Array.isArray(batchData.links)) {
      batchData.links.forEach(lData => {
        const edgeIndex = networkData.value.graph_data.edges.findIndex(
          e => e.id === lData.id
        )
        
        if (edgeIndex !== -1) {
          const edge = networkData.value.graph_data.edges[edgeIndex]
          const bandwidth = edge.details?.bandwidth_capacity || 100
          const utilization = (lData.bw / bandwidth) * 100
          
          edge.label = `${lData.bw.toFixed(1)} Mbps`
          edge.utilization = utilization
          edge.status = 'up'
          
          if (edge.details) {
            edge.details.current_throughput = lData.bw
            edge.details.utilization = utilization
          }
        }
      })
    }

    // 3. Cập nhật Switches (Heartbeat)
    if (batchData.switches && Array.isArray(batchData.switches)) {
      batchData.switches.forEach(sName => {
        const nodeIndex = networkData.value.graph_data.nodes.findIndex(
          n => n.id === sName
        )
        
        if (nodeIndex !== -1) {
          const node = networkData.value.graph_data.nodes[nodeIndex]
          if (node.details) {
            node.details.status = 'up'
          }
          node.group = 'switch'
        }
      })
    }

    lastUpdateTime.value = new Date().toISOString()
  })
  
  socket.on('disconnect', (reason) => {
    console.warn('⚠️ WebSocket disconnected:', reason)
    connectionStatus.value = 'error'
    
    if (reason === 'io server disconnect') {
      socket.connect()
    }
  })

  socket.on('connect_error', (error) => {
    console.error('❌ Connection error:', error)
    errorMessage.value = `Connection failed: ${error.message}`
    connectionStatus.value = 'error'
    isLoading.value = false
  })
}

// ============================================
// 5. LIFECYCLE HOOKS
// ============================================
onMounted(async () => {
  const isHealthy = await checkBackendHealth()
  if (!isHealthy) {
    errorMessage.value = "Backend is not reachable. Make sure Flask is running on port 5000."
    connectionStatus.value = 'error'
    isLoading.value = false
    return
  }
  
  setupWebSocket()
})

onUnmounted(() => {
  if (socket) {
    console.log('🔌 Disconnecting socket...')
    socket.disconnect()
    socket = null
  }
})

// Events từ Component con
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
</script>

<template>
  <div class="app-container">
    <Header :lastUpdate="lastUpdateTime" />

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