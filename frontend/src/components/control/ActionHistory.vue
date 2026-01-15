<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  actions: {
    type: Array,
    required: true
  }
})

const historyContainer = ref(null)
const expandedAction = ref(null)
const filterStatus = ref('all')
const autoScroll = ref(true)

const filteredActions = computed(() => {
  if (filterStatus.value === 'all') {
    return props.actions
  }
  return props.actions.filter(a => a.status === filterStatus.value)
})

const statusCounts = computed(() => {
  return {
    total: props.actions.length,
    success: props.actions.filter(a => a.status === 'SUCCESS').length,
    failed: props.actions.filter(a => a.status === 'FAILED').length,
    pending: props.actions.filter(a => a.status === 'PENDING').length
  }
})

// Auto-scroll when new actions arrive
watch(() => props.actions.length, async () => {
  if (autoScroll.value && historyContainer.value) {
    await nextTick()
    historyContainer.value.scrollTop = 0
  }
})

function toggleExpand(actionId) {
  expandedAction.value = expandedAction.value === actionId ? null : actionId
}

function getStatusIcon(status) {
  switch (status) {
    case 'SUCCESS': return '✓'
    case 'FAILED': return '✗'
    case 'PENDING': return '⏳'
    default: return '•'
  }
}

function getStatusColor(status) {
  switch (status) {
    case 'SUCCESS': return '#10b981'
    case 'FAILED': return '#ef4444'
    case 'PENDING': return '#f59e0b'
    default: return '#94a3b8'
  }
}

function formatTime(timestamp) {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('en-US', { hour12: false })
}

function formatRelativeTime(timestamp) {
  const now = new Date()
  const then = new Date(timestamp)
  const diffMs = now - then
  const diffSec = Math.floor(diffMs / 1000)
  
  if (diffSec < 60) return `${diffSec}s ago`
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
  return `${Math.floor(diffSec / 86400)}d ago`
}

function getActionTypeLabel(type) {
  const labels = {
    'IMPORT_TOPOLOGY': '📥 Import Topology',
    'TOGGLE_DEVICE': '🔌 Toggle Device',
    'TOGGLE_LINK': '🔗 Toggle Link',
    'UPDATE_LINK': '⚙️ Update Link'
  }
  return labels[type] || type
}
</script>

<template>
  <div class="action-history">
    <div class="history-header">
      <h3 class="section-title">
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
          <polyline points="17 6 23 6 23 12"/>
        </svg>
        Action History
      </h3>
      
      <div class="header-controls">
        <!-- Status Filter -->
        <select v-model="filterStatus" class="filter-select">
          <option value="all">All ({{ statusCounts.total }})</option>
          <option value="SUCCESS">Success ({{ statusCounts.success }})</option>
          <option value="FAILED">Failed ({{ statusCounts.failed }})</option>
          <option value="PENDING">Pending ({{ statusCounts.pending }})</option>
        </select>
        
        <!-- Auto-scroll Toggle -->
        <button 
          @click="autoScroll = !autoScroll" 
          class="auto-scroll-btn"
          :class="{ active: autoScroll }"
          title="Auto-scroll to newest"
        >
          <svg class="icon-small" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <polyline points="17 11 12 6 7 11"/>
            <polyline points="17 18 12 13 7 18"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- History List -->
    <div ref="historyContainer" class="history-list">
      <div 
        v-if="filteredActions.length === 0" 
        class="empty-state"
      >
        <p>📭 No actions yet</p>
        <p class="empty-hint">Actions will appear here in real-time</p>
      </div>

      <div
        v-for="action in filteredActions"
        :key="action.action_id"
        class="action-item"
        :class="{ expanded: expandedAction === action.action_id }"
        @click="toggleExpand(action.action_id)"
      >
        <!-- Action Header -->
        <div class="action-header">
          <span 
            class="status-icon" 
            :style="{ color: getStatusColor(action.status) }"
          >
            {{ getStatusIcon(action.status) }}
          </span>
          
          <div class="action-info">
            <div class="action-main">
              <span class="action-type">{{ getActionTypeLabel(action.action_type) }}</span>
              <span class="action-target">{{ action.target }}</span>
            </div>
            <div class="action-meta">
              <span class="action-time" :title="action.timestamp">
                {{ formatTime(action.timestamp) }}
              </span>
              <span class="action-relative">
                ({{ formatRelativeTime(action.timestamp) }})
              </span>
            </div>
          </div>

          <svg class="expand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </div>

        <!-- Action Details (Expanded) -->
        <div v-if="expandedAction === action.action_id" class="action-details">
          <div class="detail-row">
            <span class="detail-label">Action ID:</span>
            <span class="detail-value">{{ action.action_id }}</span>
          </div>
          
          <div v-if="action.parameters" class="detail-row">
            <span class="detail-label">Parameters:</span>
            <pre class="detail-json">{{ JSON.stringify(action.parameters, null, 2) }}</pre>
          </div>
          
          <div v-if="action.error_message" class="detail-row error">
            <span class="detail-label">Error:</span>
            <span class="detail-value">{{ action.error_message }}</span>
          </div>
          
          <div v-if="action.completed_at" class="detail-row">
            <span class="detail-label">Completed:</span>
            <span class="detail-value">{{ formatTime(action.completed_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.action-history {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #00F7F7;
  font-size: 1.2rem;
  margin: 0;
}

.icon {
  width: 24px;
  height: 24px;
  stroke: currentColor;
  stroke-width: 2;
}

.icon-small {
  width: 16px;
  height: 16px;
  stroke: currentColor;
  stroke-width: 2;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.filter-select {
  padding: 0.5rem 0.75rem;
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.filter-select:hover {
  border-color: #00F7F7;
}

.filter-select:focus {
  outline: none;
  border-color: #00F7F7;
}

.auto-scroll-btn {
  padding: 0.5rem;
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.auto-scroll-btn:hover {
  border-color: #00F7F7;
  color: #00F7F7;
}

.auto-scroll-btn.active {
  background-color: rgba(0, 247, 247, 0.1);
  border-color: #00F7F7;
  color: #00F7F7;
}

.history-list {
  max-height: 400px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding-right: 0.5rem;
}

.history-list::-webkit-scrollbar {
  width: 6px;
}

.history-list::-webkit-scrollbar-track {
  background: #1e293b;
  border-radius: 3px;
}

.history-list::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 3px;
}

.history-list::-webkit-scrollbar-thumb:hover {
  background: #00F7F7;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  color: #94a3b8;
}

.empty-state p {
  margin: 0.5rem 0;
}

.empty-hint {
  font-size: 0.85rem;
  font-style: italic;
  opacity: 0.7;
}

.action-item {
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.action-item:hover {
  border-color: #00F7F7;
  box-shadow: 0 2px 8px rgba(0, 247, 247, 0.2);
}

.action-item.expanded {
  border-color: #00F7F7;
}

.action-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.status-icon {
  font-size: 1.2rem;
  font-weight: bold;
  flex-shrink: 0;
}

.action-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.action-main {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.action-type {
  color: #e2e8f0;
  font-weight: 600;
  font-size: 0.95rem;
}

.action-target {
  color: #00F7F7;
  font-weight: 700;
  font-size: 0.9rem;
}

.action-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: #94a3b8;
}

.action-time {
  font-weight: 600;
}

.action-relative {
  opacity: 0.7;
  font-style: italic;
}

.expand-icon {
  width: 20px;
  height: 20px;
  stroke: #94a3b8;
  transition: transform 0.3s ease;
  flex-shrink: 0;
}

.action-item.expanded .expand-icon {
  transform: rotate(180deg);
}

.action-details {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #334155;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.detail-row {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-row.error {
  background-color: rgba(239, 68, 68, 0.1);
  border: 1px solid #ef4444;
  padding: 0.75rem;
  border-radius: 6px;
}

.detail-label {
  color: #94a3b8;
  font-size: 0.85rem;
  font-weight: 600;
}

.detail-value {
  color: #e2e8f0;
  font-size: 0.9rem;
}

.detail-json {
  background-color: #1e293b;
  border: 1px solid #334155;
  border-radius: 4px;
  padding: 0.75rem;
  color: #00F7F7;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  overflow-x: auto;
  margin: 0;
}
</style>