<template>
  <div class="view-switcher">
    <button 
      class="switch-btn" 
      :class="{ active: currentView === 'live' }"
      @click="$emit('change-view', 'live')"
    >
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
      </svg>
      <span>Live Monitoring</span>
    </button>

    <button 
      class="switch-btn" 
      :class="{ active: currentView === 'analytics' }"
      @click="$emit('change-view', 'analytics')"
    >
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <line x1="12" y1="20" x2="12" y2="10"/>
        <line x1="18" y1="20" x2="18" y2="4"/>
        <line x1="6" y1="20" x2="6" y2="16"/>
      </svg>
      <span>Analytics Dashboard</span>
    </button>
  </div>
</template>

<script setup>
defineProps({
  currentView: {
    type: String,
    default: 'live'
  }
})

defineEmits(['change-view'])
</script>

<style scoped>
.view-switcher {
  display: flex;
  gap: 0.5rem;
  padding: 0.5rem;
  background-color: rgba(15, 23, 42, 0.8);
  border-radius: 12px;
  backdrop-filter: blur(10px);
}

.switch-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background-color: transparent;
  border: 2px solid #334155;
  border-radius: 8px;
  color: #94a3b8;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.switch-btn:hover {
  background-color: rgba(51, 65, 85, 0.5);
  border-color: #00F7F7;
  color: #00F7F7;
}

.switch-btn.active {
  background-color: #00F7F7;
  border-color: #00F7F7;
  color: #0f172a;
  box-shadow: 0 4px 12px rgba(0, 247, 247, 0.4);
}

.icon {
  width: 20px;
  height: 20px;
  stroke-width: 2.5;
}

@media (max-width: 768px) {
  .view-switcher {
    flex-direction: column;
  }
  
  .switch-btn span {
    display: none;
  }
}
</style>