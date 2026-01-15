<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'

const props = defineProps({
  devices: {
    type: Array,
    required: true
  }
})

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

const selectedDevice = ref(null)
const isProcessing = ref(false)
const notification = ref(null)

const selectedDeviceObj = computed(() => {
  if (!selectedDevice.value) return null
  return props.devices.find(d => d.name === selectedDevice.value)
})

const canEnable = computed(() => {
  if (!selectedDeviceObj.value) return false
  return selectedDeviceObj.value.status === 'offline'
})

const canDisable = computed(() => {
  if (!selectedDeviceObj.value) return false
  return selectedDeviceObj.value.status === 'up'
})

async function toggleDevice(action) {
  if (!selectedDevice.value || isProcessing.value) return
  
  isProcessing.value = true
  
  try {
    const response = await axios.post(
      `${API_BASE_URL}/control/device/${selectedDevice.value}/toggle`,
      { action: action }
    )
    
    if (response.data.status === 'success') {
      showNotification(`✓ ${action === 'enable' ? 'Enabled' : 'Disabled'} ${selectedDevice.value}`, 'success')
    } else {
      showNotification(`✗ Failed: ${response.data.message}`, 'error')
    }
  } catch (error) {
    console.error('Error toggling device:', error)
    showNotification(`✗ Error: ${error.response?.data?.error || error.message}`, 'error')
  } finally {
    isProcessing.value = false
  }
}

function showNotification(message, type) {
  notification.value = { message, type }
  setTimeout(() => {
    notification.value = null
  }, 3000)
}

function getStatusColor(status) {
  switch (status) {
    case 'up': return '#10b981'
    case 'offline': return '#6b7280'
    case 'high-load': return '#f59e0b'
    default: return '#94a3b8'
  }
}

function getStatusIcon(status) {
  switch (status) {
    case 'up': return '🟢'
    case 'offline': return '⚫'
    case 'high-load': return '🟡'
    default: return '⚪'
  }
}
</script>

<template>
  <div class="device-controller">
    <h3 class="section-title">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
        <line x1="8" y1="21" x2="16" y2="21"/>
        <line x1="12" y1="17" x2="12" y2="21"/>
      </svg>
      Device Controller
    </h3>

    <!-- Notification -->
    <div v-if="notification" class="notification" :class="notification.type">
      {{ notification.message }}
    </div>

    <!-- Device Selection -->
    <div class="form-group">
      <label>Select Device:</label>
      <select v-model="selectedDevice" class="device-select">
        <option :value="null">-- Choose a device --</option>
        <optgroup label="Hosts">
          <option 
            v-for="device in devices.filter(d => d.type === 'host')" 
            :key="device.name"
            :value="device.name"
          >
            {{ device.name }} ({{ device.status }})
          </option>
        </optgroup>
        <optgroup label="Switches">
          <option 
            v-for="device in devices.filter(d => d.type === 'switch')" 
            :key="device.name"
            :value="device.name"
          >
            {{ device.name }} ({{ device.status }})
          </option>
        </optgroup>
      </select>
    </div>

    <!-- Device Info -->
    <div v-if="selectedDeviceObj" class="device-info">
      <div class="info-row">
        <span class="label">Name:</span>
        <span class="value">{{ selectedDeviceObj.name }}</span>
      </div>
      <div class="info-row">
        <span class="label">Type:</span>
        <span class="value">{{ selectedDeviceObj.type }}</span>
      </div>
      <div class="info-row">
        <span class="label">Status:</span>
        <span class="value" :style="{ color: getStatusColor(selectedDeviceObj.status) }">
          {{ getStatusIcon(selectedDeviceObj.status) }} {{ selectedDeviceObj.status }}
        </span>
      </div>
    </div>

    <!-- Control Buttons -->
    <div class="button-group">
      <button 
        @click="toggleDevice('enable')" 
        class="control-btn enable"
        :disabled="!canEnable || isProcessing"
      >
        <span v-if="isProcessing && canEnable">⏳</span>
        <span v-else>▶️</span>
        Enable
      </button>
      
      <button 
        @click="toggleDevice('disable')" 
        class="control-btn disable"
        :disabled="!canDisable || isProcessing"
      >
        <span v-if="isProcessing && canDisable">⏳</span>
        <span v-else>⏸️</span>
        Disable
      </button>
    </div>

    <!-- Help Text -->
    <div class="help-text">
      <p v-if="!selectedDevice">
        ℹ️ Select a device to control
      </p>
      <p v-else-if="selectedDeviceObj.status === 'up'">
        ✓ Device is online. You can disable it.
      </p>
      <p v-else-if="selectedDeviceObj.status === 'offline'">
        ⚠️ Device is offline. You can enable it.
      </p>
    </div>
  </div>
</template>

<style scoped>
.device-controller {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #00F7F7;
  font-size: 1.2rem;
  margin: 0 0 1rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #334155;
}

.icon {
  width: 24px;
  height: 24px;
  stroke: currentColor;
  stroke-width: 2;
}

.notification {
  padding: 0.75rem;
  border-radius: 6px;
  font-size: 0.9rem;
  animation: slideIn 0.3s ease;
}

.notification.success {
  background-color: rgba(16, 185, 129, 0.2);
  border: 1px solid #10b981;
  color: #10b981;
}

.notification.error {
  background-color: rgba(239, 68, 68, 0.2);
  border: 1px solid #ef4444;
  color: #ef4444;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  color: #94a3b8;
  font-size: 0.9rem;
  font-weight: 600;
}

.device-select {
  padding: 0.75rem;
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.device-select:hover {
  border-color: #00F7F7;
}

.device-select:focus {
  outline: none;
  border-color: #00F7F7;
  box-shadow: 0 0 0 3px rgba(0, 247, 247, 0.1);
}

.device-info {
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-row .label {
  color: #94a3b8;
  font-size: 0.9rem;
}

.info-row .value {
  color: #e2e8f0;
  font-weight: 600;
}

.button-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.control-btn {
  padding: 0.75rem 1.5rem;
  border: 2px solid;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.control-btn.enable {
  background-color: rgba(16, 185, 129, 0.1);
  border-color: #10b981;
  color: #10b981;
}

.control-btn.enable:hover:not(:disabled) {
  background-color: #10b981;
  color: #0f172a;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
}

.control-btn.disable {
  background-color: rgba(239, 68, 68, 0.1);
  border-color: #ef4444;
  color: #ef4444;
}

.control-btn.disable:hover:not(:disabled) {
  background-color: #ef4444;
  color: #0f172a;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
}

.control-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.help-text {
  background-color: rgba(0, 247, 247, 0.05);
  border-left: 3px solid #00F7F7;
  padding: 0.75rem;
  border-radius: 4px;
  font-size: 0.9rem;
  color: #94a3b8;
}

.help-text p {
  margin: 0;
}
</style>