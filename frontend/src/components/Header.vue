<template>
  <header class="app-header">
    <div class="header-title">
      <img :src="iconHeader" class="header-icon" alt="Network Icon" />
      <span title="Digital Twin Network Dashboard">Digital Twin Network Dashboard</span>
    </div>

    <!-- Thời gian cập nhật -->
    <div class="time-stats">
      <span>Latest Update:</span>
      <span class="time-value">{{ updateCount }}</span>
      <span class="time-value active">{{ lastUpdateTime }}</span>
    </div>
  </header>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import iconHeader from '@/assets/icons/internet.png'

// State thời gian
const lastUpdateTime = ref('00:00:00')
const updateCount = ref('00:00:00')

// Cập nhật đồng hồ thực tế
onMounted(() => {
  setInterval(() => {
    const now = new Date()
    lastUpdateTime.value = now.toLocaleTimeString('vi-VN', { hour12: false })
  }, 1000)
})
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  height: 60px;
  background-color: #0f172a;
  font-family: 'Arial', sans-serif;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  border-bottom: 1px solid #334155;
}

.header-title {
  display: flex;
  align-items: center;
}

.header-title span {
  color: #00F7F7 !important; 
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-shadow: 0 0 8px rgba(34, 211, 238, 0.4); /* Hiệu ứng phát sáng nhẹ */
}

/* Cập nhật lại màu chữ cho phần thời gian */
.time-stats {
  display: flex;
  align-items: center;
  font-size: 0.95rem;
  font-weight: 500;
  color: #ffffff; 
}

.time-stats span {
  margin-left: 0.75rem;
}

.time-value {
  padding: 6px 10px;
  background-color: #00F7F7;
  border-radius: 6px;
  font-weight: 600;

  transition: background-color 0.3s ease;
  color: #000000; /* Chữ trắng trong ô xám */
}

.time-value.active {
  background-color: #00F7F7;
  color: #000000;
  font-weight: 600;
}

/* Hover effect */
.time-value:hover {
  background-color: #ffffff;
}

.time-value.active:hover {
  background-color: #ffffff;
}

.header-icon {
  width: 28px;
  height: 28px;
  margin-right: 0.75rem;
}

/* Responsive */
@media (max-width: 768px) {
  .app-header {
    flex-direction: column;
    height: auto;
    padding: 1rem;
  }
  .header-title {
    margin-bottom: 0.5rem;
  }
  .time-stats {
    margin-top: 0.5rem;
    justify-content: center;
    width: 100%;
  }
  .header-title span {
    font-size: 1.1rem;
  }
}
</style>