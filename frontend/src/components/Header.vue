<template>
  <header class="app-header">
    <i></i> <span>Digital Twin Network Dashboard</span>

    <div class="time-stats">
      <span>Cập nhật lần cuối:</span>
      <span class="time-value">#035:12</span>
      <span class="time-value active">16:35:12</span>
    </div>
  </header>
</template>

<script setup>
// Nơi này sau này có thể chứa logic
</script>

<style scoped>
/* 'scoped': CSS này CHỈ áp dụng cho file Header.vue */
.app-header {
  display: flex; /* Xếp các item (icon, title, time) theo hàng ngang */
  align-items: center; /* Căn giữa theo chiều dọc */
  padding: 0 1.5rem;
  height: 50px;
  background-color: #1e293b; /* Màu nền tối (Dark background) */
  color: #e2e8f0; /* Màu chữ sáng (Light text) */
  font-size: 1.1rem;
  font-weight: 600;
}

.app-header i {
  margin-right: 0.75rem;
  font-style: italic;
  font-weight: bold;
}

.time-stats {
  margin-left: auto; /* Đẩy mục thời gian này về sát bên phải */
  font-size: 0.9rem;
  font-weight: 400;
}

.time-stats span {
  margin-left: 0.5rem;
}

.time-value {
  padding: 4px 8px;
  background-color: #334155;
  border-radius: 4px;
}

.time-value.active {
  background-color: #16a34a; /* Màu xanh lá cây */
  color: white;
}
</style>