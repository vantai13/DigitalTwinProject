<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

// Import các "viên gạch"
import Header from './components/Header.vue'
import TopologyView from './components/TopologyView.vue'
import InfoPanel from './components/InfoPanel.vue'

// === STATE CHÍNH ===
const networkData = ref(null)
const isLoading = ref(true)
const errorMessage = ref(null)

// State để theo dõi đối tượng đang được chọn
const selectedNodeId = ref(null)
const selectedEdgeId = ref(null) // <-- STATE MỚI

// === GỌI API ===
async function fetchData() {
  try {
    // Lưu ý: Đảm bảo API này trả về dữ liệu 'edges'
    // với các trường 'id', 'utilization', 'status', v.v.
    const response = await axios.get('http://localhost:5000/api/network/status')
    
    networkData.value = response.data
    console.log("Dữ liệu đã tải thành công:", response.data)
  } catch (error) {
    console.error("Lỗi khi gọi API:", error)
    errorMessage.value = "Không thể kết nối đến Backend (Flask)."
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchData()
  
  // (Tùy chọn) Cập nhật dữ liệu mỗi 5 giây
  // setInterval(fetchData, 5000);
})

// === HÀM XỬ LÝ SỰ KIỆN ===

// Khi một NODE được chọn
function handleNodeSelected(nodeId) {
  selectedNodeId.value = nodeId
  selectedEdgeId.value = null // Bỏ chọn edge
  console.log("Node được chọn:", selectedNodeId.value)
}

// Khi một EDGE (LINK) được chọn (MỚI)
function handleEdgeSelected(edgeId) {
  selectedEdgeId.value = edgeId
  selectedNodeId.value = null // Bỏ chọn node
  console.log("Edge được chọn:", selectedEdgeId.value)
}

// Khi người dùng click ra ngoài (MỚI)
function handleSelectionCleared() {
  selectedNodeId.value = null
  selectedEdgeId.value = null
}
</script>

<template>
  <div class="app-container">
    <Header />

    <div v-if="networkData" class="main-content">
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

    <div v-if="isLoading" class="loading-screen">
      Đang tải dữ liệu từ Flask...
    </div>
    
    <div v-if="errorMessage" class="loading-screen error">
      LỖI: {{ errorMessage }}
    </div>

  </div>
</template>

<style>
/* (Toàn bộ CSS global của bạn ở đây) */
body, html {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: Arial, sans-serif; 
  background-color: #0f172a;
}
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.loading-screen {
  position: fixed;
  bottom: 10px;
  left: 10px;
  background-color: rgba(255, 255, 255, 0.9);
  color: black;
  padding: 10px;
  border-radius: 8px;
  z-index: 1000;
  font-size: 0.8rem;
  border: 1px solid #ccc;
}
.loading-screen.error {
  background-color: #ffcccc;
  color: #a00;
  border-color: #a00;
}
</style>