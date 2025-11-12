<template>
  <div class="topology-view">
    <h3>NETWORK TOPOLOGY</h3>
    <div class="diagram-container" ref="networkContainer"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { Network } from 'vis-network/standalone'
import 'vis-network/styles/vis-network.css'

// Import icon
import iconHost from '@/assets/icons/laptop.png'
import iconSwitch from '@/assets/icons/switch.png'

const props = defineProps(['graphData'])
const emit = defineEmits(['node-selected'])
const networkContainer = ref(null)
const networkInstance = ref(null)

function initializeNetwork() {
  if (!networkContainer.value || !props.graphData) {
    console.error("TopologyView: Container hoặc graphData chưa sẵn sàng.")
    return
  }

  const data = {
    nodes: props.graphData.nodes,
    edges: props.graphData.edges
  }

  const options = {
    physics: {
      enabled: true,
      stabilization: { iterations: 200 }, // Tăng để layout đẹp hơn
      solver: 'barnesHut',
      barnesHut: {
        gravitationalConstant: -12000,
        centralGravity: 0.08,
        springLength: 120,
        springConstant: 0.06,
        damping: 0.12
      }
    },
    interaction: {
      hover: true,
      tooltipDelay: 200,
      navigationButtons: false,  // XÓA NÚT ĐIỀU HƯỚNG
      keyboard: false
    },
    nodes: {
      font: {
        color: '#00F7F7',        // CHỮ MÀU CYAN ĐẸP
        size: 13,
        face: 'Arial',
        strokeWidth: 3,
        strokeColor: '#0f172a'
      },
      shapeProperties: { useBorderWithImage: true },
      borderWidth: 3,
      size: 32
    },
    edges: {
      width: 2.5,
      color: {
        color: '#475569',
        highlight: '#00FFFF',
        hover: '#00F7F7'
      },
      arrows: { to: { enabled: false } },
      font: {
        color: '#00F7F7',        // CHỮ TRÊN CẠNH CŨNG CYAN
        size: 11,
        align: 'middle',
        strokeWidth: 4,
        strokeColor: '#0f172a'
      },
      smooth: { type: 'continuous' }
    },
    groups: {
      host: {
        shape: 'image',
        image: iconHost,
        color: {
          border: '#0ea5e9',
          background: '#0f172a',
          highlight: { border: '#0ea5e9', background: '#1e293b' },
          hover: { border: '#0ea5e9', background: '#1e293b' }
        },
        // GLOW SIÊU ĐẸP CHO HOST
        shadow: {
          enabled: true,
          color: 'rgba(14, 165, 233, 0.8)', // Màu xanh cyan phát sáng
          size: 25,
          x: 0,
          y: 0
        }
      },
      switch: {
        shape: 'image',
        image: iconSwitch,
        color: {
          border: '#f97316',
          background: '#0f172a',
          highlight: { border: '#f97316', background: '#1e293b' },
          hover: { border: '#f97316', background: '#1e293b' }
        },
        // GLOW SIÊU ĐẸP CHO SWITCH
        shadow: {
          enabled: true,
          color: 'rgba(249, 115, 22, 0.8)', // Màu cam phát sáng
          size: 25,
          x: 0,
          y: 0
        }
      },
      offline: {
        color: { border: '#7f1d1d', background: '#0f172a' },
        shadow: { enabled: false }
      }
    }
  }

  try {
    networkInstance.value = new Network(networkContainer.value, data, options)

    networkInstance.value.on('selectNode', (properties) => {
      if (properties.nodes.length > 0) {
        emit('node-selected', properties.nodes[0])
      }
    })

    networkInstance.value.on('deselectNode', () => {
      emit('node-selected', null)
    })

    console.log("TopologyView: Khởi tạo Vis.js THÀNH CÔNG!")
  } catch (error) {
    console.error("LỖI KHI KHỞI TẠO VIS.JS:", error)
  }
}

onMounted(() => {
  initializeNetwork()
})

watch(() => props.graphData, (newData) => {
  if (newData && networkInstance.value) {
    networkInstance.value.setData({
      nodes: newData.nodes,
      edges: newData.edges
    })
  } else if (newData && !networkInstance.value) {
    initializeNetwork()
  }
}, { deep: true })
</script>

<style scoped>
.topology-view {
  flex: 1;
  padding: 1.5rem;
  background-color: #0f172a;
  color: #94a3b8;
  display: flex;
  flex-direction: column;
}

h3 {
 color: #00F7F7;       
  margin-bottom: 1rem;
  flex-shrink: 0;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  font-weight: 700;
  text-shadow: 0 0 10px rgba(0, 247, 247, 0.5);

}

.diagram-container {
  flex: 1;
  border: 1px solid #334155;
  border-radius: 12px;
  background-color: #0f172a;
  min-height: 600px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  
  border-bottom: 1px solid #334155;
  padding-bottom: 1rem;

  border-bottom: 3px solid #00F7F7;     /* Viền cyan phát sáng */
  box-shadow: 0 6px 20px rgba(0, 247, 247, 0.3); /* Ánh sáng nhẹ phía dưới */

  
  

}

/* ẨN HOÀN TOÀN NÚT ĐIỀU HƯỚNG */
:deep(.vis-navigation) {
  display: none !important;
}
</style>