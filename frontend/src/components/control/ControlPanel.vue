<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { io } from 'socket.io-client'
import DeviceController from './DeviceController.vue'
import LinkController from './LinkController.vue'
import ActionHistory from './ActionHistory.vue'

// ============================================
// CONFIGURATION
// ============================================
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'
const SOCKET_URL = import.meta.env.VITE_SOCKET_URL || 'http://localhost:5000'

// ============================================
// STATE
// ============================================
const networkData = ref(null)
const actionHistory = ref([])
const isLoading = ref(true)
const errorMessage = ref(null)

let socket = null

// ============================================
// COMPUTED
// ============================================
const devices = computed(() => {
  if (!networkData.value) return []
  
  const hosts = networkData.value.graph_data.nodes
    .filter(n => n.group && n.group.startsWith('host'))
    .map(n => ({
      name: n.id,
      type: 'host',
      status: n.details?.status || 'unknown'
    }))
  
  const switches = networkData.value.graph_data.nodes
    .filter(n => n.group && n.group.startsWith('switch'))
    .map(n => ({
      name: n.id,
      type: 'switch',
      status: n.details?.status || 'unknown'
    }))
  
  return [...hosts, ...switches]
})

const links = computed(() => {
  if (!networkData.value) return []
  
  return networkData.value.graph_data.edges.map(e => ({
    id: e.id,
    from: e.from,
    to: e.to,
    status: e.status || 'unknown',
    bandwidth: e.details?.bandwidth_capacity || 100,
    currentThroughput: e.details?.current_throughput || 0,
    utilization: e.utilization || 0
  }))
})

// ============================================
// METHODS
// ============================================
async function loadNetworkData() {
  try {
    const response = await axios.get(`${API_BASE_URL}/network/status`)
    networkData.value = response.data
    isLoading.value = false
  } catch (error) {
    console.error('Error loading network data:', error)
    errorMessage.value = 'Failed to load network data'
    isLoading.value = false
  }
}

async function loadActionHistory() {
  try {
    const response = await axios.get(`${API_BASE_URL}/control/actions/history?limit=50`)
    if (response.data.status === 'success') {
      actionHistory.value = response.data.actions
    }
  } catch (error) {
    console.error('Error loading action history:', error)
  }
}

function setupWebSocket() {
  socket = io(SOCKET_URL, {
    transports: ['websocket', 'polling'],
    reconnection: true
  })

  socket.on('connect', () => {
    console.log('✅ WebSocket connected')
  })

  socket.on('initial_state', (data) => {
    networkData.value = data
    isLoading.value = false
  })

  socket.on('network_batch_update', (data) => {
    if (!networkData.value) return
    
    // Update hosts
    data.hosts?.forEach(h => {
      const node = networkData.value.graph_data.nodes.find(n => n.id === h.name)
      if (node && node.details) {
        node.details.status = h.status
        node.details.cpu_utilization = h.cpu
        node.details.memory_usage = h.mem
      }
    })
    
    // Update links
    data.links?.forEach(l => {
      const edge = networkData.value.graph_data.edges.find(e => e.id === l.id)
      if (edge) {
        edge.status = l.status
        if (edge.details) {
          edge.details.current_throughput = l.bw
        }
      }
    })
  })

  // Listen for action updates
  socket.on('action_started', (action) => {
    console.log('🔵 Action started:', action)
    actionHistory.value.unshift(action)
  })

  socket.on('action_completed', (action) => {
    console.log('✅ Action completed:', action)
    updateActionInHistory(action)
  })

  socket.on('action_failed', (action) => {
    console.log('❌ Action failed:', action)
    updateActionInHistory(action)
  })
}

function updateActionInHistory(updatedAction) {
  const index = actionHistory.value.findIndex(a => a.action_id === updatedAction.action_id)
  if (index !== -1) {
    actionHistory.value[index] = updatedAction
  } else {
    actionHistory.value.unshift(updatedAction)
  }
}

// ============================================
// LIFECYCLE
// ============================================
onMounted(async () => {
  await loadNetworkData()
  await loadActionHistory()
  setupWebSocket()
})

onUnmounted(() => {
  if (socket) {
    socket.disconnect()
  }
})
</script>

<template>
  <div class="control-panel">
    <!-- Header -->
    <div class="panel-header">
      <h2>🎛️ CONTROL PANEL</h2>
      <div class="header-stats">
        <span class="stat-badge">Devices: {{ devices.length }}</span>
        <span class="stat-badge">Links: {{ links.length }}</span>
        <span class="stat-badge">Actions: {{ actionHistory.length }}</span>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-container">
      <div class="loading-spinner"></div>
      <p>Loading network data...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="errorMessage" class="error-container">
      <p>{{ errorMessage }}</p>
      <button @click="loadNetworkData" class="retry-btn">Retry</button>
    </div>

    <!-- Main Content -->
    <div v-else class="panel-content">
      <!-- Controllers Grid -->
      <div class="controllers-grid">
        <!-- Device Controller -->
        <div class="controller-card">
          <DeviceController :devices="devices" />
        </div>

        <!-- Link Controller -->
        <div class="controller-card">
          <LinkController :links="links" />
        </div>
      </div>

      <!-- Action History -->
      <div class="history-section">
        <ActionHistory :actions="actionHistory" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.control-panel {
  background-color: #0f172a;
  color: #e2e8f0;
  min-height: 100vh;
  padding: 1.5rem;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #00F7F7;
}

.panel-header h2 {
  color: #00F7F7;
  font-size: 1.8rem;
  margin: 0;
  text-shadow: 0 0 10px rgba(0, 247, 247, 0.5);
}

.header-stats {
  display: flex;
  gap: 1rem;
}

.stat-badge {
  background-color: rgba(0, 247, 247, 0.1);
  border: 1px solid #00F7F7;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
}

.loading-container,
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
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

.retry-btn {
  margin-top: 1rem;
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

.retry-btn:hover {
  background-color: #ffffff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 247, 247, 0.4);
}

.panel-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.controllers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 1.5rem;
}

.controller-card {
  background-color: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.history-section {
  background-color: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

@media (max-width: 768px) {
  .panel-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
  
  .header-stats {
    width: 100%;
    flex-wrap: wrap;
  }
  
  .controllers-grid {
    grid-template-columns: 1fr;
  }
}
</style>