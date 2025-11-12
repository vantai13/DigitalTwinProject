<template>
  <aside class="info-panel">
    <h3>INFO PANEL</h3>
    
    <div class="info-card" v-if="networkData">
      <h4>Tổng quan Mạng</h4>
      <p>Tổng số Hosts: {{ networkData.total_hosts }}</p>
      <p>Tổng số Switches: {{ networkData.total_switches }}</p>
    </div>
    
    <div class="info-card">
      <h4>Chi tiết đối tượng chọn</h4>
      
      <div v-if="selectedNodeDetails">
        <p><strong>Tên:</strong> {{ selectedNodeDetails.details.name }}</p>
        <p><strong>Loại:</strong> {{ selectedNodeDetails.group }}</p>
        
        <template v-if="selectedNodeDetails.group === 'host'">
          <p><strong>IP:</strong> {{ selectedNodeDetails.details.ip_address }}</p>
          <p><strong>Trạng thái:</strong> {{ selectedNodeDetails.details.status }}</p>
          <p><strong>CPU:</strong> {{ selectedNodeDetails.details.cpu_utilization }}%</p>
          <p><strong>Memory:</strong> {{ selectedNodeDetails.details.memory_usage }}%</p>
        </template>
        
        <template v-if="selectedNodeDetails.group === 'switch'">
          <p><strong>DPID:</strong> {{ selectedNodeDetails.details.dpid }}</p>
          <p><strong>Trạng thái:</strong> {{ selectedNodeDetails.details.status }}</p>
        </template>
      </div>
      
      <div v-else>
        <p class="placeholder-text">(Nhấn vào một node trên sơ đồ để xem chi tiết)</p>
      </div>
    </div>

  </aside>
</template>

<script setup>
// 1. IMPORT CÔNG CỤ
import { computed } from 'vue'

// 2. KHAI BÁO PROPS
// Nhận 2 props từ App.vue
const props = defineProps(['networkData', 'selectedNodeId'])

// 3. TẠO "BIẾN TÍNH TOÁN" (Computed Property)
// Đây là "bộ não" của InfoPanel
const selectedNodeDetails = computed(() => {
  // Nếu 1 trong 2 prop chưa có, trả về null
  if (!props.selectedNodeId || !props.networkData) {
    return null
  }
  
  // Tìm trong mảng 'nodes' của 'graph_data'
  // (Chúng ta dùng .find() của JavaScript)
  const node = props.networkData.graph_data.nodes.find(
    (n) => n.id === props.selectedNodeId
  )
  
  return node || null // Trả về node tìm được, hoặc null
})
</script>

<style scoped>
/* ... (CSS của bạn từ Giai đoạn 2.1 không đổi) ... */
.info-panel {
  width: 350px;
  flex-shrink: 0;
  background-color: #1e293b;
  padding: 1.5rem;
  color: #94a3b8;
  border-left: 1px solid #334155;
  /* Thêm overflow để cuộn nếu panel quá dài */
  overflow-y: auto; 
}
h3 { color: #e2e8f0; margin-bottom: 1rem; }
.info-card {
  background-color: #0f172a;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}
.info-card h4 { color: #e2e8f0; margin-bottom: 0.75rem; }

/* Thêm style cho phần chi tiết */
.info-card p {
  margin: 0.5rem 0;
  font-size: 0.9rem;
}
.info-card p strong {
  color: #e2e8f0;
  min-width: 80px; /* Căn chỉnh cho đẹp */
  display: inline-block;
}
.placeholder-text {
  font-style: italic;
  color: #64748b;
  font-size: 0.9rem;
}
</style>