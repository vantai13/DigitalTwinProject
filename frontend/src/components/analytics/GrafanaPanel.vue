<template>
  <div class="grafana-panel" :class="{ 'full-width': fullWidth }">
    <div class="panel-header">
      <h4>{{ title }}</h4>
      <div class="panel-actions">
        <button 
          class="action-btn" 
          @click="refresh"
          title="Refresh"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
          </svg>
        </button>
        
        <button 
          class="action-btn" 
          @click="openInGrafana"
          title="Open in Grafana"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
            <polyline points="15 3 21 3 21 9"/>
            <line x1="10" y1="14" x2="21" y2="3"/>
          </svg>
        </button>
      </div>
    </div>

    <div class="iframe-container" v-if="!isLoading && !hasError">
      <iframe
        :key="iframeKey"
        :src="embedUrl"
        frameborder="0"
        @load="onLoad"
        @error="onError"
      ></iframe>
    </div>

    <div v-if="isLoading" class="panel-loading">
      <div class="loading-spinner"></div>
      <p>Loading dashboard...</p>
    </div>

    <div v-if="hasError" class="panel-error">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <p>Failed to load dashboard</p>
      <button @click="refresh">Retry</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  embedUrl: {
    type: String,
    required: true
  },
  fullWidth: {
    type: Boolean,
    default: false
  }
})

const isLoading = ref(true)
const hasError = ref(false)
const iframeKey = ref(0)

const grafanaBaseUrl = computed(() => {
  try {
    const url = new URL(props.embedUrl)
    // Chuyển từ /d-solo/ sang /d/ để mở full dashboard
    const dashboardPath = props.embedUrl.replace('/d-solo/', '/d/')
    return dashboardPath.split('?')[0]
  } catch {
    return 'http://localhost:3000'
  }
})

function refresh() {
  isLoading.value = true
  hasError.value = false
  iframeKey.value++
}

function onLoad() {
  isLoading.value = false
  hasError.value = false
}

function onError() {
  isLoading.value = false
  hasError.value = true
}

function openInGrafana() {
  window.open(grafanaBaseUrl.value, '_blank')
}
</script>

<style scoped>
.grafana-panel {
  background-color: #1e293b;
  border-radius: 12px;
  border: 1px solid #334155;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
}

.grafana-panel.full-width {
  grid-column: 1 / -1;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background-color: #0f172a;
  border-bottom: 1px solid #334155;
}

.panel-header h4 {
  margin: 0;
  color: #00F7F7;
  font-size: 1rem;
  font-weight: 600;
}

.panel-actions {
  display: flex;
  gap: 0.5rem;
}

.action-btn {
  width: 32px;
  height: 32px;
  padding: 0;
  background-color: transparent;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn:hover {
  background-color: #334155;
  border-color: #00F7F7;
  color: #00F7F7;
}

.action-btn svg {
  width: 16px;
  height: 16px;
  stroke-width: 2;
}

.iframe-container {
  flex: 1;
  position: relative;
  background-color: #0f172a;
}

.iframe-container iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.panel-loading,
.panel-error {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  gap: 1rem;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #334155;
  border-top-color: #00F7F7;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.panel-error svg {
  width: 48px;
  height: 48px;
  stroke: #ef4444;
}

.panel-error button {
  padding: 0.5rem 1.5rem;
  background-color: #00F7F7;
  color: #0f172a;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.panel-error button:hover {
  background-color: #ffffff;
  transform: translateY(-2px);
}
</style>