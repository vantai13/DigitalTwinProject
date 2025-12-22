<template>
  <div class="grafana-panel-wrapper">
    <!-- Header của panel -->
    <div class="panel-header">
      <h3>{{ title }}</h3>
      <button @click="refreshPanel" class="refresh-btn">
        🔄 Refresh
      </button>
    </div>

    <!-- Container chứa iframe -->
    <div class="iframe-container">
      <!-- 🔥 FIX LỖI 2: iframe LUÔN tồn tại, không phụ thuộc v-if -->
      <iframe
        :key="iframeKey"
        :src="embedUrl"
        frameborder="0"
        @load="onLoad"
        @error="onError"
        class="grafana-iframe"
      ></iframe>

      <!-- 🔥 Loading overlay (chồng lên iframe) -->
      <div v-if="isLoading" class="panel-loading">
        <div class="loading-spinner"></div>
        <p>Loading dashboard...</p>
      </div>

      <!-- Error overlay -->
      <div v-if="hasError" class="panel-error">
        <p>❌ Failed to load dashboard</p>
        <button @click="retryLoad">Retry</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'GrafanaPanel',
  props: {
    title: {
      type: String,
      default: 'Grafana Panel'
    },
    embedUrl: {
      type: String,
      required: true
    },
    fullWidth: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      isLoading: true,
      hasError: false,
      iframeKey: 0  // Dùng để force re-render iframe
    }
  },
  methods: {
    onLoad() {
      console.log('✅ Grafana panel loaded:', this.title)
      this.isLoading = false
      this.hasError = false
    },
    onError() {
      console.error('❌ Grafana panel error:', this.title)
      this.isLoading = false
      this.hasError = true
    },
    refreshPanel() {
      this.isLoading = true
      this.hasError = false
      this.iframeKey++  // Force iframe reload
    },
    retryLoad() {
      this.refreshPanel()
    }
  }
}
</script>

<style scoped>
.grafana-panel-wrapper {
  background: #1e1e1e;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #2a2a2a;
  border-bottom: 1px solid #3a3a3a;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  color: #fff;
}

.refresh-btn {
  background: #4CAF50;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.3s;
}

.refresh-btn:hover {
  background: #45a049;
}

/* 🔥 QUAN TRỌNG: Container dùng position relative */
.iframe-container {
  position: relative;
  width: 100%;
  height: 400px;
  background: #1a1a1a;
}

/* 🔥 Iframe chiếm toàn bộ container */
.grafana-iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: none;
}

/* 🔥 Loading overlay chồng LÊN iframe */
.panel-loading {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: rgba(26, 26, 26, 0.95);
  z-index: 10;
}

.loading-spinner {
  border: 4px solid #3a3a3a;
  border-top: 4px solid #4CAF50;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.panel-loading p {
  margin-top: 16px;
  color: #aaa;
}

.panel-error {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: rgba(26, 26, 26, 0.95);
  z-index: 10;
}

.panel-error p {
  color: #f44336;
  margin-bottom: 16px;
}

.panel-error button {
  background: #2196F3;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.panel-error button:hover {
  background: #1976D2;
}
</style>