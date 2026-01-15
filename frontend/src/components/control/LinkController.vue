<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'

const props = defineProps({
  links: {
    type: Array,
    required: true
  }
})

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

const selectedLink = ref(null)
const isProcessing = ref(false)
const notification = ref(null)

// Condition editors
const bandwidth = ref(100)
const delay = ref('0')
const loss = ref(0)

const selectedLinkObj = computed(() => {
  if (!selectedLink.value) return null
  return props.links.find(l => l.id === selectedLink.value)
})

const canToggleUp = computed(() => {
  if (!selectedLinkObj.value) return false
  return selectedLinkObj.value.status === 'down'
})

const canToggleDown = computed(() => {
  if (!selectedLinkObj.value) return false
  return selectedLinkObj.value.status === 'up' || selectedLinkObj.value.status === 'warning' || selectedLinkObj.value.status === 'high-load'
})

function onLinkSelected() {
  if (selectedLinkObj.value) {
    // Reset values to current link settings
    bandwidth.value = selectedLinkObj.value.bandwidth
    delay.value = '0'
    loss.value = 0
  }
}

async function toggleLink(action) {
  if (!selectedLink.value || isProcessing.value) return
  
  isProcessing.value = true
  
  try {
    const response = await axios.post(
      `${API_BASE_URL}/control/link/${selectedLink.value}/toggle`,
      { action: action }
    )
    
    if (response.data.status === 'success') {
      showNotification(`✓ Link ${selectedLink.value} set to ${action.toUpperCase()}`, 'success')
    } else {
      showNotification(`✗ Failed: ${response.data.message}`, 'error')
    }
  } catch (error) {
    console.error('Error toggling link:', error)
    showNotification(`✗ Error: ${error.response?.data?.error || error.message}`, 'error')
  } finally {
    isProcessing.value = false
  }
}

async function updateConditions() {
  if (!selectedLink.value || isProcessing.value) return
  
  // Validate inputs
  if (bandwidth.value <= 0) {
    showNotification('⚠️ Bandwidth must be greater than 0', 'error')
    return
  }
  
  if (loss.value < 0 || loss.value > 100) {
    showNotification('⚠️ Packet loss must be between 0 and 100%', 'error')
    return
  }
  
  isProcessing.value = true
  
  try {
    const conditions = {
      bandwidth: bandwidth.value
    }
    
    // Only send delay if > 0
    const delayNum = parseInt(delay.value)
    if (delayNum > 0) {
      conditions.delay = `${delayNum}ms`
    }
    
    // Only send loss if > 0
    if (loss.value > 0) {
      conditions.loss = loss.value
    }
    
    const response = await axios.put(
      `${API_BASE_URL}/control/link/${selectedLink.value}/update`,
      conditions
    )
    
    if (response.data.status === 'success') {
      showNotification(`✓ Link conditions updated`, 'success')
    } else {
      showNotification(`✗ Failed: ${response.data.message}`, 'error')
    }
  } catch (error) {
    console.error('Error updating link:', error)
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
    case 'down': return '#6b7280'
    case 'warning': return '#f59e0b'
    case 'high-load': return '#ef4444'
    default: return '#94a3b8'
  }
}

function getStatusIcon(status) {
  switch (status) {
    case 'up': return '🟢'
    case 'down': return '⚫'
    case 'warning': return '🟡'
    case 'high-load': return '🔴'
    default: return '⚪'
  }
}
</script>

<template>
  <div class="link-controller">
    <h3 class="section-title">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
      </svg>
      Link Controller
    </h3>

    <!-- Notification -->
    <div v-if="notification" class="notification" :class="notification.type">
      {{ notification.message }}
    </div>

    <!-- Link Selection -->
    <div class="form-group">
      <label>Select Link:</label>
      <select v-model="selectedLink" @change="onLinkSelected" class="link-select">
        <option :value="null">-- Choose a link --</option>
        <option 
          v-for="link in links" 
          :key="link.id"
          :value="link.id"
        >
          {{ link.id }} ({{ link.status }})
        </option>
      </select>
    </div>

    <!-- Link Info -->
    <div v-if="selectedLinkObj" class="link-info">
      <div class="info-row">
        <span class="label">Link:</span>
        <span class="value">{{ selectedLinkObj.from }} ↔ {{ selectedLinkObj.to }}</span>
      </div>
      <div class="info-row">
        <span class="label">Status:</span>
        <span class="value" :style="{ color: getStatusColor(selectedLinkObj.status) }">
          {{ getStatusIcon(selectedLinkObj.status) }} {{ selectedLinkObj.status }}
        </span>
      </div>
      <div class="info-row">
        <span class="label">Throughput:</span>
        <span class="value">{{ selectedLinkObj.currentThroughput.toFixed(1) }} Mbps</span>
      </div>
      <div class="info-row">
        <span class="label">Utilization:</span>
        <span class="value">{{ selectedLinkObj.utilization.toFixed(1) }}%</span>
      </div>
    </div>

    <!-- Toggle Buttons -->
    <div class="button-group">
      <button 
        @click="toggleLink('up')" 
        class="control-btn up"
        :disabled="!canToggleUp || isProcessing"
      >
        <span v-if="isProcessing && canToggleUp">⏳</span>
        <span v-else>▲</span>
        Link Up
      </button>
      
      <button 
        @click="toggleLink('down')" 
        class="control-btn down"
        :disabled="!canToggleDown || isProcessing"
      >
        <span v-if="isProcessing && canToggleDown">⏳</span>
        <span v-else>▼</span>
        Link Down
      </button>
    </div>

    <!-- Network Conditions Editor -->
    <div v-if="selectedLink" class="conditions-editor">
      <h4 class="editor-title">Network Conditions</h4>
      
      <!-- Bandwidth Slider -->
      <div class="form-group">
        <label>Bandwidth: <span class="value-display">{{ bandwidth }} Mbps</span></label>
        <input 
          v-model.number="bandwidth" 
          type="range" 
          min="1" 
          max="1000" 
          step="1"
          class="slider"
        />
      </div>

      <!-- Delay Input -->
      <div class="form-group">
        <label>Delay: <span class="value-display">{{ delay }} ms</span></label>
        <input 
          v-model.number="delay" 
          type="number" 
          min="0" 
          max="500"
          class="number-input"
          placeholder="Enter delay in ms"
        />
      </div>

      <!-- Packet Loss Slider -->
      <div class="form-group">
        <label>Packet Loss: <span class="value-display">{{ loss }}%</span></label>
        <input 
          v-model.number="loss" 
          type="range" 
          min="0" 
          max="100" 
          step="0.1"
          class="slider"
          :class="{ 'high-loss': loss > 10 }"
        />
        <p v-if="loss > 10" class="warning-text">⚠️ High packet loss! Network may be unstable.</p>
      </div>

      <!-- Apply Button -->
      <button 
        @click="updateConditions" 
        class="apply-btn"
        :disabled="isProcessing"
      >
        <span v-if="isProcessing">⏳ Applying...</span>
        <span v-else>✓ Apply Changes</span>
      </button>
    </div>

    <!-- Help Text -->
    <div class="help-text">
      <p v-if="!selectedLink">
        ℹ️ Select a link to control
      </p>
      <p v-else>
        💡 Adjust network conditions above and click "Apply Changes"
      </p>
    </div>
  </div>
</template>

<style scoped>
.link-controller {
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
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.value-display {
  color: #00F7F7;
  font-weight: 700;
}

.link-select {
  padding: 0.75rem;
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.link-select:hover {
  border-color: #00F7F7;
}

.link-select:focus {
  outline: none;
  border-color: #00F7F7;
  box-shadow: 0 0 0 3px rgba(0, 247, 247, 0.1);
}

.link-info {
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

.control-btn.up {
  background-color: rgba(16, 185, 129, 0.1);
  border-color: #10b981;
  color: #10b981;
}

.control-btn.up:hover:not(:disabled) {
  background-color: #10b981;
  color: #0f172a;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
}

.control-btn.down {
  background-color: rgba(239, 68, 68, 0.1);
  border-color: #ef4444;
  color: #ef4444;
}

.control-btn.down:hover:not(:disabled) {
  background-color: #ef4444;
  color: #0f172a;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
}

.control-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.conditions-editor {
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.editor-title {
  color: #00F7F7;
  font-size: 1rem;
  margin: 0;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #334155;
}

.slider {
  width: 100%;
  height: 6px;
  background: #334155;
  border-radius: 3px;
  outline: none;
  -webkit-appearance: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  background: #00F7F7;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 0 10px rgba(0, 247, 247, 0.5);
}

.slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  background: #00F7F7;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 0 10px rgba(0, 247, 247, 0.5);
  border: none;
}

.slider.high-loss::-webkit-slider-thumb {
  background: #ef4444;
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.5);
}

.slider.high-loss::-moz-range-thumb {
  background: #ef4444;
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.5);
}

.number-input {
  padding: 0.75rem;
  background-color: #1e293b;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 1rem;
  transition: all 0.3s ease;
}

.number-input:focus {
  outline: none;
  border-color: #00F7F7;
  box-shadow: 0 0 0 3px rgba(0, 247, 247, 0.1);
}

.warning-text {
  color: #f59e0b;
  font-size: 0.85rem;
  margin: 0;
  font-style: italic;
}

.apply-btn {
  padding: 0.75rem 1.5rem;
  background-color: #00F7F7;
  border: none;
  border-radius: 8px;
  color: #0f172a;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s ease;
}

.apply-btn:hover:not(:disabled) {
  background-color: #ffffff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 247, 247, 0.4);
}

.apply-btn:disabled {
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