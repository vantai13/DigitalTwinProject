<template>
  <div class="topology-view">
    <h3>NETWORK TOPOLOGY</h3>
    <div class="diagram-container" ref="networkContainer"></div>
  </div>
</template>

<script setup>
// 2. IMPORT CÁC CÔNG CỤ CẦN THIẾT
import { ref, onMounted } from 'vue'
import { Network } from 'vis-network'

import 'vis-network/styles/vis-network.css' // Import CSS của Vis.js

// 3. KHAI BÁO PROPS & EMITS
// Khai báo rằng component này nhận 1 prop tên 'graphData'
const props = defineProps(['graphData'])
// Khai báo rằng component này có thể phát ra 1 event tên 'node-selected'
const emit = defineEmits(['node-selected'])

// 4. TẠO DOM REF
// Tạo một biến 'ref' có tên TRÙNG VỚI tên trong template
const networkContainer = ref(null)

// 5. VẼ SƠ ĐỒ KHI COMPONENT ĐƯỢC TẢI
onMounted(() => {
  // Dữ liệu (nodes, edges) đến từ prop

  // === BƯỚC 1: KIỂM TRA DỮ LIỆU ĐÃ ĐẾN NƠI CHƯA ===
  console.log("TopologyView: Dữ liệu prop đã nhận:", props.graphData) 

  // === BƯỚC 2: KIỂM TRA CONTAINER ĐÃ TỒN TẠI CHƯA ===
  console.log("TopologyView: Container DOM element:", networkContainer.value)

  const data = {
    nodes: props.graphData.nodes,
    edges: props.graphData.edges
  }
  
  // Tùy chọn (options) cho sơ đồ (để trông giống Dark Mode)
  const options = {
    nodes: {
      shape: 'box', // Bạn có thể đổi thành 'image' sau
      font: { color: '#ffffff' }
    },
    edges: {
      color: { color: '#848484', highlight: '#ffffff' },
      arrows: { to: { enabled: false } }
    },
    physics: {
      enabled: true // Bật hiệu ứng vật lý
    },
    interaction: {
      hover: true // Cho phép hover
    }
  }

  if (networkContainer.value && props.graphData) {
    // === BƯỚC 3: KIỂM TRA LỖI KHI KHỞI TẠO ===
    try {
      const network = new Network(networkContainer.value, data, options)
      
      // === BƯỚC 4: XÁC NHẬN THÀNH CÔNG ===
      console.log("TopologyView: Khởi tạo Vis.js THÀNH CÔNG!")
      
      network.on('click', (properties) => {
        // ... (code emit của bạn)
      })
    } catch (error) {
      // Nếu có lỗi ở đây, nó sẽ bị bắt lại
      console.error("TopologyView: LỖI KHI KHỞI TẠO VIS.JS:", error)
    }
  } else {
    console.error("TopologyView: Container DOM hoặc dữ liệu graphData không tồn tại!")
  }

  // Khởi tạo sơ đồ!
  // 'network' là một đối tượng của Vis.js
  if (networkContainer.value) {
    const network = new Network(networkContainer.value, data, options)

    // 6. BẮT SỰ KIỆN CLICK (Dòng chảy 2 ⬆️)
    network.on('click', (properties) => {
      // 'properties.nodes' là một MẢNG chứa ID của các node được click
      if (properties.nodes.length > 0) {
        const clickedNodeId = properties.nodes[0] // Lấy ID của node đầu tiên
        // Phát event "node-selected" lên cho App.vue
        emit('node-selected', clickedNodeId)
      } else {
        // Nếu click vào khoảng trắng (không click vào node nào)
        emit('node-selected', null) // Gửi 'null' để xóa lựa chọn
      }
    })
  }
})
</script>

<style scoped>
.topology-view {
  flex: 1;
  padding: 1.5rem;
  background-color: #0f172a;
  color: #94a3b8;
  /* Quan trọng: Cho phép container co giãn */
  display: flex;
  flex-direction: column;
}

h3 {
  color: #e2e8f0;
  margin-bottom: 1rem;
  flex-shrink: 0; /* Không cho h3 bị co lại */
}

/* Quan trọng: Cho sơ đồ chiếm hết phần còn lại */
.diagram-container {
  flex: 1; /* Chiếm hết không gian dọc còn lại */
  border: 1px solid #334155; /* Viền mỏng thay cho dashed */
  border-radius: 8px;

  min-height: 600px;
}
</style>