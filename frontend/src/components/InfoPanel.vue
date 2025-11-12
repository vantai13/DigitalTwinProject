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

      <template v-else>
        <p class="placeholder-text">(Nhấn vào một node trên sơ đồ để xem chi tiết)</p>
      </template>
    </div>

  </aside>
</template>

<script setup>
import { computed } from 'vue'
import iconNetwork from '@/assets/icons/database.svg'
import iconNode from '@/assets/icons/server.svg'
import iconWarning from '@/assets/icons/alert-triangle.svg'
import iconSitemap from '@/assets/icons/sitemap.png'
import iconHosting from '@/assets/icons/hosting.png'

const props = defineProps(['networkData', 'selectedNodeId'])

const selectedNodeDetails = computed(() => {
  if (!props.selectedNodeId || !props.networkData) {
    return null
  }
  const node = props.networkData.graph_data.nodes.find(
    (n) => n.id === props.selectedNodeId
  )
  return node || null
})
</script>

<style scoped>
.info-panel {
  width: 350px;
  flex-shrink: 0;
  background-color: #1e293b;
  padding: 1.5rem;
  color: #94a3b8; /* Màu chữ thường (label) giữ nguyên cho dễ đọc */
  border-left: 1px solid #334155;
  overflow-y: auto;
}

h3 {
  color: #00F7F7; /* 🌟 SỬA MÀU 1 🌟 */
  margin-bottom: 1rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  text-shadow: 0 0 10px rgba(0, 247, 247, 0.7); /* Thêm shadow cho đẹp */
}

.info-card {
  background-color: #0f172a;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  border: 1px solid #334155;
}

.info-card h4 {
  color: #00F7F7; /* 🌟 SỬA MÀU 2 🌟 */
  margin-bottom: 1rem;
  margin-top: 0;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #334155;
  padding-bottom: 0.75rem;
  text-shadow: 0 0 8px rgba(0, 247, 247, 0.6); /* Thêm shadow */
}

.info-card p {
  margin: 0.6rem 0;
  font-size: 0.9rem;
  display: flex;
  justify-content: space-between;
}

.info-card p span {
  color: #94a3b8; /* Giữ màu label xám để làm nổi bật giá trị */
}

.info-card p strong {
  color: #00F7F7; /* 🌟 SỬA MÀU 3 🌟 */
  font-weight: 600;
}

.placeholder-text {
  margin-top: 1.5rem;
  font-style: italic;
  color: #64748b;
  font-size: 0.9rem;
  text-align: center;
}

/* Giữ nguyên màu đỏ/vàng cho CẢNH BÁO
  vì chúng cần phải nổi bật 
*/
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

/* 🌟 SỬA MÀU ICON 🌟 */
.icon {
  width: 50px;
  height: 50px;
  margin-right: 0.5rem;
  /* Filter này sẽ đổi màu SVG thành #00F7F7 */

}

.icon-warning {
  width: 16px;
  height: 16px;
  margin-right: 0.5rem;
  /* Giữ filter vàng cho icon warning */
  filter: invert(82%) sepia(21%) saturate(2333%) hue-rotate(345deg) brightness(99%) contrast(92%);
}
</style>