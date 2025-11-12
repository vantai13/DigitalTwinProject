<script setup>
// === BƯỚC 1: IMPORT CÁC CÔNG CỤ ===
import { ref, onMounted } from 'vue' // Import từ Vue
import axios from 'axios'           // Import "người đưa thư"

// Import 3 component "viên gạch" (Như Giai đoạn 2.1)
import Header from './components/Header.vue'
import TopologyView from './components/TopologyView.vue'
import InfoPanel from './components/InfoPanel.vue'


// === BƯỚC 2: TẠO "STATE" ĐỂ LƯU DỮ LIỆU ===
// 'ref' tạo ra một "cái hộp" có tính "phản ứng" (reactive).
// Bất cứ khi nào giá trị trong hộp này thay đổi, Vue sẽ
// tự động cập nhật mọi nơi trong HTML đang sử dụng nó.
// Chúng ta khởi tạo nó là 'null' (chưa có dữ liệu).
const networkData = ref(null)
const isLoading = ref(true) // Thêm một state để biết khi nào đang tải
const errorMessage = ref(null) // Thêm state để báo lỗi

// === BƯỚC 3: ĐỊNH NGHĨA HÀM GỌI API ===
// Chúng ta tạo 1 hàm riêng để lấy dữ liệu.
// 'async' báo hiệu đây là một hàm bất đồng bộ (sẽ mất thời gian).
async function fetchData() {
  try {
    // 'await' sẽ "chờ" cho axios gọi xong API
    // Đây chính là URL Flask từ Giai đoạn 1.
    const response = await axios.get('http://localhost:5000/api/network/status')
    
    // Gán dữ liệu nhận được vào "hộp" state.
    // LƯU Ý: Phải dùng .value khi làm việc với 'ref'
    networkData.value = response.data 
    
    console.log("Dữ liệu đã tải thành công:", response.data)
  } catch (error) {
    // Nếu có lỗi (Flask sập, CORS sai, 404, v.v.)
    console.error("Lỗi khi gọi API:", error)
    errorMessage.value = "Không thể kết nối đến Backend (Flask)."
  } finally {
    // Dù thành công hay thất bại, cũng tắt màn hình loading
    isLoading.value = false
  }
}

// === BƯỚC 4: SỬ DỤNG "LIFECYCLE HOOK" ===
// 'onMounted' là một hàm đặc biệt của Vue.
// Nó sẽ tự động chạy 1 lần DUY NHẤT ngay sau khi
// component App.vue được render (gắn) lên màn hình.
// Đây là thời điểm hoàn hảo để gọi API lần đầu tiên.
onMounted(() => {
  fetchData() // Gọi hàm chúng ta vừa định nghĩa
})

// . Tạo một state MỚI để lưu trữ ID của node đang được chọn
//    Nó bắt đầu là 'null' (chưa chọn gì cả)
const selectedNodeId = ref(null)

// 2. Tạo một hàm "xử lý" (handler) sẽ được gọi
//    khi component con (TopologyView) "phát" (emit) sự kiện
function handleNodeSelected(nodeId) {
  selectedNodeId.value = nodeId // Cập nhật state với ID node được chọn
  console.log("Node được chọn:", selectedNodeId.value)
}



</script>

<template>
  <div class="app-container">
    <Header />

    <div v-if="networkData" class="main-content">
      <TopologyView 
      :graphData="networkData.graph_data"
      @node-selected="handleNodeSelected"
      />
      <InfoPanel
      :networkData="networkData"
      :selectedNodeId="selectedNodeId"
      
      
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
/* (Toàn bộ CSS global từ Giai đoạn 2.1 của bạn ở đây) */
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

/* Thêm CSS cho phần debug (để dễ nhìn) */
.loading-screen {
  position: fixed;
  bottom: 10px;
  left: 10px;
  background-color: rgba(255, 255, 255, 0.9);
  color: black;
  padding: 10px;
  border-radius: 8px;
  z-index: 1000;
  max-height: 200px;
  overflow-y: auto;
  font-size: 0.8rem;
  border: 1px solid #ccc;
}
.loading-screen.error {
  background-color: #ffcccc;
  color: #a00;
  border-color: #a00;
}
</style>