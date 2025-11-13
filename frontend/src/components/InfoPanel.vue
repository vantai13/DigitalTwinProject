<template>
  <aside class="info-panel">
    <h3>INFO PANEL</h3>

    <div class="info-card" v-if="networkData">
      <h4>
        <img :src="iconSitemap" class="icon" /> Tổng quan Mạng
      </h4>
      <p><span>Tổng số Hosts:</span> <strong>{{ networkData.total_hosts }}</strong></p>
      <p><span>Tổng số Switches:</span> <strong>{{ networkData.total_switches }}</strong></p>
    </div>

    <div class="info-card">
      <h4>
        <img :src="iconHosting" class="icon" /> Chi tiết đối tượng chọn
      </h4>
      
      <template v-if="selectedNodeDetails">
        <div v-if="selectedNodeDetails.details.status === 'offline'" class="status-warning">
          <img :src="iconWarning" class="icon-warning" /> Thiết bị đang NGOẠI TUYẾN!
        </div>
        <div v-if="selectedNodeDetails.details.status === 'high-load'" class="status-warning load">
          <img :src="iconWarning" class="icon-warning" /> Thiết bị đang TẢI CAO!
        </div>

        <p><span>Tên:</span> <strong>{{ selectedNodeDetails.details.name }}</strong></p>
        <p><span>Loại:</span> <strong>{{ selectedNodeDetails.group }}</strong></p>

        <template v-if="selectedNodeDetails.group === 'host'">
          <p><span>IP:</span> <strong>{{ selectedNodeDetails.details.ip_address }}</strong></p>
          <p><span>Trạng thái:</span> <strong>{{ selectedNodeDetails.details.status }}</strong></p>
          <p><span>CPU:</span> <strong>{{ selectedNodeDetails.details.cpu_utilization }}%</strong></p>
          <p><span>Memory:</span> <strong>{{ selectedNodeDetails.details.memory_usage }}%</strong></p>
        </template>

        <template v-if="selectedNodeDetails.group === 'switch'">
          <p><span>DPID:</span> <strong>{{ selectedNodeDetails.details.dpid }}</strong></p>
          <p><span>Trạng thái:</span> <strong>{{ selectedNodeDetails.details.status }}</strong></p>
        </template>
      </template>

      <template v-else-if="selectedEdgeDetails">
        <div v-if="selectedEdgeDetails.status === 'down'" class="status-warning">
          <img :src="iconWarning" class="icon-warning" /> Liên kết đang NGOẠI TUYẾN!
        </div>
        <div v-else-if="selectedEdgeDetails.utilization > 90" class="status-warning">
          <img :src="iconWarning" class="icon-warning" /> TẢI RẤT CAO ({{ selectedEdgeDetails.utilization }}%)
        </div>
         <div v-else-if="selectedEdgeDetails.utilization > 70" class="status-warning load">
          <img :src="iconWarning" class="icon-warning" /> TẢI CAO ({{ selectedEdgeDetails.utilization }}%)
        </div>

        <p><span>Tên Link:</span> <strong>{{ selectedEdgeDetails.label }}</strong></p>
        <p><span>Từ:</span> <strong>{{ selectedEdgeDetails.from }}</strong></p>
        <p><span>Tới:</span> <strong>{{ selectedEdgeDetails.to }}</strong></p>
        <p><span>Loại:</span> <strong>{{ selectedEdgeDetails.type || 'N/A' }}</strong></p>
        <p><span>Trạng thái:</span> <strong>{{ selectedEdgeDetails.status }}</strong></p>
        <p><span>Độ trễ (Latency):</span> <strong>{{ selectedEdgeDetails.latency || 'N/A' }}</strong></p>
        <p><span>Tải (Utilization):</span> <strong>{{ selectedEdgeDetails.utilization }}%</strong></p>
      </template>

      <template v-else>
        <p class="placeholder-text">(Nhấn vào một node hoặc một link trên sơ đồ để xem chi tiết)</p>
      </template>
    </div>

  </aside>
</template>

<script setup>
import { computed } from 'vue'
import iconWarning from '@/assets/icons/alert-triangle.svg'
import iconSitemap from '@/assets/icons/sitemap.png'
import iconHosting from '@/assets/icons/hosting.png'

// MỚI: Thêm 'selectedEdgeId' vào props
const props = defineProps(['networkData', 'selectedNodeId', 'selectedEdgeId'])

// Computed cho NODE (Giữ nguyên)
const selectedNodeDetails = computed(() => {
  if (!props.selectedNodeId || !props.networkData) {
    return null
  }
  const node = props.networkData.graph_data.nodes.find(
    (n) => n.id === props.selectedNodeId
  )
  return node || null
})

// Computed cho EDGE (MỚI)
const selectedEdgeDetails = computed(() => {
  if (!props.selectedEdgeId || !props.networkData) {
    return null
  }
  // Tìm edge trong mảng data gốc
  const edge = props.networkData.graph_data.edges.find(
    (e) => e.id === props.selectedEdgeId
  )
  return edge || null
})
</script>

<style scoped>
/* (Toàn bộ CSS của InfoPanel.vue ở đây) */
.info-panel {
  width: 350px;
  flex-shrink: 0;
  background-color: #1e293b;
  padding: 1.5rem;
  color: #94a3b8;
  border-left: 1px solid #334155;
  overflow-y: auto;
}
h3 {
  color: #00F7F7;
  margin-bottom: 1rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  text-shadow: 0 0 10px rgba(0, 247, 247, 0.7);
}
.info-card {
  background-color: #0f172a;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  border: 1px solid #334155;
}
.info-card h4 {
  color: #00F7F7;
  margin-bottom: 1rem;
  margin-top: 0;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #334155;
  padding-bottom: 0.75rem;
  text-shadow: 0 0 8px rgba(0, 247, 247, 0.6);
}
.info-card p {
  margin: 0.6rem 0;
  font-size: 0.9rem;
  display: flex;
  justify-content: space-between;
}
.info-card p span {
  color: #94a3b8;
}
.info-card p strong {
  color: #00F7F7;
  font-weight: 600;
}
.placeholder-text {
  margin-top: 1.5rem;
  font-style: italic;
  color: #64748b;
  font-size: 0.9rem;
  text-align: center;
}
.status-warning {
  padding: 0.75rem;
  border-radius: 6px;
  font-weight: bold;
  margin-bottom: 1rem;
  text-align: center;
  background-color: #5a1d1d;
  border: 1px solid #dc2626;
  color: #fca5a5;
  display: flex;
  align-items: center;
  justify-content: center;
}
.status-warning.load {
  background-color: #5a4a1d;
  border: 1px solid #dca026;
  color: #fce0a5;
}
.icon {
  width: 50px;
  height: 50px;
  margin-right: 0.5rem;
}
.icon-warning {
  width: 16px;
  height: 16px;
  margin-right: 0.5rem;
  filter: invert(82%) sepia(21%) saturate(2333%) hue-rotate(345deg) brightness(99%) contrast(92%);
}
</style>