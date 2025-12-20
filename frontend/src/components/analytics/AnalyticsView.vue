<template>
  <div class="analytics-view">
    <!-- Dashboard Selector -->
    <div class="dashboard-selector">
      <button
        v-for="dashboard in dashboards"
        :key="dashboard.id"
        class="dashboard-tab"
        :class="{ active: selectedDashboard === dashboard.id }"
        @click="selectDashboard(dashboard.id)"
      >
        <component :is="dashboard.icon" />
        <span>{{ dashboard.name }}</span>
      </button>
    </div>

    <!-- Dashboard Content -->
    <div class="dashboard-content" :class="`layout-${currentLayout}`">
      <template v-if="selectedDashboard === 'host'">
        <GrafanaPanel
          title="CPU Usage Over Time"
          :embed-url="getEmbedUrl('adrnqwx', 1)"
        />
        <GrafanaPanel
          title="CPU Status Gauge"
          :embed-url="getEmbedUrl('adrnqwx', 2)"
        />
        <GrafanaPanel
          title="Memory Usage Over Time"
          :embed-url="getEmbedUrl('adrnqwx', 4)"
        />
        <GrafanaPanel
          title="Host Status Overview"
          :embed-url="getEmbedUrl('adrnqwx', 5)"
          :full-width="true"
        />
      </template>

      <template v-else-if="selectedDashboard === 'link'">
        <GrafanaPanel
          title="Link Throughput"
          :embed-url="getEmbedUrl('add97wb', 1)"
          :full-width="true"
        />
        <GrafanaPanel
          title="Packet Loss Rate"
          :embed-url="getEmbedUrl('add97wb', 3)"
        />
        <GrafanaPanel
          title="Current Link Status"
          :embed-url="getEmbedUrl('add97wb', 5)"
        />
      </template>

      <template v-else-if="selectedDashboard === 'overview'">
        <GrafanaPanel
          title="Network Overview - CPU"
          :embed-url="getEmbedUrl('adrnqwx', 1)"
        />
        <GrafanaPanel
          title="Network Overview - Links"
          :embed-url="getEmbedUrl('add97wb', 1)"
        />
        <GrafanaPanel
          title="Host Status Table"
          :embed-url="getEmbedUrl('adrnqwx', 5)"
          :full-width="true"
        />
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, h } from 'vue'
import GrafanaPanel from './GrafanaPanel.vue'

const GRAFANA_BASE_URL = import.meta.env.VITE_GRAFANA_URL || 'http://localhost:3000'

const selectedDashboard = ref('host')

// Icon components (inline SVG)
const HostIcon = () => h('svg', { 
  viewBox: '0 0 24 24', 
  fill: 'none', 
  stroke: 'currentColor',
  'stroke-width': '2'
}, [
  h('rect', { x: '2', y: '3', width: '20', height: '14', rx: '2' }),
  h('line', { x1: '8', y1: '21', x2: '16', y2: '21' }),
  h('line', { x1: '12', y1: '17', x2: '12', y2: '21' })
])

const LinkIcon = () => h('svg', {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  'stroke-width': '2'
}, [
  h('path', { d: 'M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71' }),
  h('path', { d: 'M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71' })
])

const OverviewIcon = () => h('svg', {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  'stroke-width': '2'
}, [
  h('rect', { x: '3', y: '3', width: '7', height: '7' }),
  h('rect', { x: '14', y: '3', width: '7', height: '7' }),
  h('rect', { x: '14', y: '14', width: '7', height: '7' }),
  h('rect', { x: '3', y: '14', width: '7', height: '7' })
])

const dashboards = [
  { 
    id: 'overview', 
    name: 'Overview', 
    icon: OverviewIcon,
    layout: 'grid'
  },
  { 
    id: 'host', 
    name: 'Host Performance', 
    icon: HostIcon,
    layout: 'grid'
  },
  { 
    id: 'link', 
    name: 'Link Performance', 
    icon: LinkIcon,
    layout: 'grid'
  }
]

const currentLayout = computed(() => {
  return dashboards.find(d => d.id === selectedDashboard.value)?.layout || 'grid'
})

function selectDashboard(id) {
  selectedDashboard.value = id
}

function getEmbedUrl(dashboardUid, panelId) {
  if (!dashboardUid) {
    console.error(`⚠️ Missing UID`)
    return ''
  }
  
  // ✅ SỬ DỤNG TRỰC TIẾP UID TỪ THAM SỐ
  const baseUrl = `${GRAFANA_BASE_URL}/d-solo/${dashboardUid}/dashboard`
  const params = new URLSearchParams({
    orgId: '1',
    from: 'now-5m',
    to: 'now',
    panelId: panelId.toString(),
    theme: 'dark',
    refresh: '5s'
  })
  
  const fullUrl = `${baseUrl}?${params.toString()}`
  console.log('📊 Grafana URL:', fullUrl) // ← Debug log
  
  return fullUrl
}
</script>

<style scoped>
.analytics-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #0f172a;
  padding: 1.5rem;
  gap: 1.5rem;
  overflow: hidden;
}

.dashboard-selector {
  display: flex;
  gap: 0.75rem;
  background-color: rgba(30, 41, 59, 0.5);
  padding: 0.75rem;
  border-radius: 12px;
  border: 1px solid #334155;
  flex-shrink: 0;
}

.dashboard-tab {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background-color: transparent;
  border: 1px solid #334155;
  border-radius: 8px;
  color: #94a3b8;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.dashboard-tab svg {
  width: 20px;
  height: 20px;
}

.dashboard-tab:hover {
  background-color: rgba(51, 65, 85, 0.5);
  border-color: #00F7F7;
  color: #00F7F7;
}

.dashboard-tab.active {
  background-color: #00F7F7;
  border-color: #00F7F7;
  color: #0f172a;
  box-shadow: 0 4px 12px rgba(0, 247, 247, 0.3);
}

.dashboard-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.dashboard-content.layout-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: 1.5rem;
  align-content: start;
}

/* Scrollbar styling */
.dashboard-content::-webkit-scrollbar {
  width: 8px;
}

.dashboard-content::-webkit-scrollbar-track {
  background: #1e293b;
  border-radius: 4px;
}

.dashboard-content::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 4px;
}

.dashboard-content::-webkit-scrollbar-thumb:hover {
  background: #00F7F7;
}

@media (max-width: 1200px) {
  .dashboard-content.layout-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .analytics-view {
    padding: 1rem;
  }
  
  .dashboard-selector {
    overflow-x: auto;
  }
  
  .dashboard-tab span {
    display: none;
  }
}
</style>