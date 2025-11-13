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
import iconHost from '@/assets/icons/laptop.png'
import iconSwitch from '@/assets/icons/switch.png'



const props = defineProps(['graphData'])
const emit = defineEmits(['node-selected', 'edge-selected', 'selection-cleared'])

const networkContainer = ref(null)
const networkInstance = ref(null)

function processEdges(edges) {
  const highThreshold = 90
  const mediumThreshold = 70

  if (!Array.isArray(edges)) {
    console.error("processEdges: Dữ liệu edges không phải là mảng", edges)
    return []
  }

  return edges.map(edge => {
    let colorVal
    let arrowsConfig = { to: { enabled: false } }
    let isDashed = false
    let shadowConfig = { enabled: false }

    // Logic màu sắc
    if (edge.status === 'down') {
      colorVal = '#475569'
      isDashed = true
    } else if (edge.utilization > highThreshold) {
      colorVal = '#F60000'
    } else if (edge.utilization > mediumThreshold) {
      colorVal = '#f97316'
    } else {
      colorVal = '#00F7F7'
    }

    // Animation lưu lượng
    if (edge.status === 'up' && edge.utilization > 0) {
      
      let arrowSpeed = 1; // Tốc độ mặc định

      // Chỉ cần tính tốc độ
      if (edge.utilization > highThreshold) { // Tải cao
        arrowSpeed = 1.5; // Nhanh
      } else if (edge.utilization > mediumThreshold) { // Tải trung bình
        arrowSpeed = 1.2; // Vừa
      }
      // Tải thấp sẽ giữ nguyên màu xanh/tốc độ 1

      // Cấu hình mũi tên động của bạn
      arrowsConfig = {
        to: {
          enabled: true,

          // BẮT BUỘC dùng lại 'moving-arrow' để nó di chuyển
          type: 'moving-arrow',

          // 1. Tinh chỉnh kích thước mũi tên
          // scaleFactor: 1 là mặc định. 
          // 1.2 là to hơn 20%. Bạn có thể thử 1.5 hoặc 2.0
          scaleFactor: 1.2,

          // 2. Tinh chỉnh tốc độ/tần suất
          // 'length' vẫn hoạt động với 'moving-arrow'
          // Số càng NHỎ, mũi tên càng GẦN NHAU và chạy càng NHANH.
          length: 40 / arrowSpeed
        }
      }
    }




    // Glow cho link up
    if (edge.status !== 'down') {
      shadowConfig = {
        enabled: true,
        color: colorVal,
        size: 20,
        x: 0,
        y: 0
      }
    }

    return {
      ...edge,
      color: {
        color: colorVal,
        highlight: colorVal,
        hover: colorVal
      },
      width: 2.5,
      arrows: arrowsConfig,
      dashes: isDashed,
      smooth: {
        type: 'continuous'
      },
      shadow: shadowConfig
    }
  })
}

function processNodes(nodes) {
  if (!Array.isArray(nodes)) {
    console.error("processNodes: Dữ liệu nodes không phải là mảng", nodes)
    return []
  }

  return nodes.map(node => {
    const status = node.details?.status
    let finalGroup = node.group

    if (status === 'offline') {
      // Dùng group offline riêng cho host/switch để có viền nét đứt
      if (node.group === 'host') {
        finalGroup = 'host-offline'
      } else if (node.group === 'switch') {
        finalGroup = 'switch-offline'
      }
    } else if (status === 'high-load') {
      if (node.group === 'host') {
        finalGroup = 'host-high-load'
      } else if (node.group === 'switch') {
        finalGroup = 'switch-high-load'
      }
    }

    return { ...node, group: finalGroup }
  })
}

function initializeNetwork() {
  if (!networkContainer.value || !props.graphData) {
    console.error("TopologyView: Container hoặc graphData chưa sẵn sàng.")
    return
  }

  const processedEdges = processEdges(props.graphData.edges)
  const processedNodes = processNodes(props.graphData.nodes)

  const data = {
    nodes: processedNodes,
    edges: processedEdges
  }

  const options = {
    physics: {
      enabled: true,
      stabilization: { iterations: 200 },
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
      navigationButtons: false,
      keyboard: false,
      selectConnectedEdges: false,
      selectable: true,
      multiselect: false
    },
    nodes: {
      font: {
        color: '#00F7F7',
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
      color: { highlight: '#FFFFFF', opacity: 1.0 },
      selectionWidth: 4,
      font: {
        color: '#00F7F7',
        size: 11,
        align: 'middle',
        strokeWidth: 4,
        strokeColor: '#0f172a',
      },
      arrows: {
    to: { enabled: true }
      }
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
        shadow: {
          enabled: true,
          color: 'rgba(14, 165, 233, 0.8)',
          size: 25,
          x: 0,
          y: 0
        }
      },
      'host-offline': {
        shape: 'image',
        image: iconHost,
        color: {
          border: '#475569',
          background: '#0f172a',
          highlight: { border: '#94a3b8', background: '#1e293b' },
          hover: { border: '#94a3b8', background: '#1e293b' }
        },
        borderWidth: 3,
        borderDashes: [8, 8],
        opacity: 0.6, 
        shadow: { enabled: false }
      },
      'host-high-load': {
        shape: 'image',
        image: iconHost,
        color: {
          border: '#F60000',
          background: '#0f172a',
          highlight: { border: '#F60000', background: '#1e293b' },
          hover: { border: '#F60000', background: '#1e293b' }
        },
        shadow: {
          enabled: true,
          color: 'rgba(246, 0, 0, 0.8)',
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
        shadow: {
          enabled: true,
          color: 'rgba(249, 115, 22, 0.8)',
          size: 25,
          x: 0,
          y: 0
        }
      },
      'switch-offline': {
        shape: 'image',
        image: iconSwitch,
        color: {
          border: '#475569',
          background: '#0f172a'
        },
        borderWidth: 3,
        borderDashes: [8, 8],
        opacity: 0.6,
        shadow: { enabled: false }
      },
      'switch-high-load': {
        shape: 'image',
        image: iconSwitch,
        color: {
          border: '#F60000',
          background: '#0f172a',
          highlight: { border: '#F60000', background: '#1e293b' },
          hover: { border: '#F60000', background: '#1e293b' }
        },
        shadow: {
          enabled: true,
          color: 'rgba(246, 0, 0, 0.8)',
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

    networkInstance.value.on('selectNode', properties => {
      if (properties.nodes.length > 0) {
        emit('node-selected', properties.nodes[0])
      }
    })

    networkInstance.value.on('selectEdge', properties => {
      if (properties.edges.length > 0) {
        emit('edge-selected', properties.edges[0])
      }
    })

    networkInstance.value.on('click', properties => {
      if (properties.nodes.length === 0 && properties.edges.length === 0) {
        emit('selection-cleared')
      }
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
    const processedEdges = processEdges(newData.edges)
    const processedNodes = processNodes(newData.nodes)

    networkInstance.value.body.data.nodes.update(processedNodes)
    networkInstance.value.body.data.edges.update(processedEdges)
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
  border-bottom: 3px solid #00F7F7;
  box-shadow: 0 6px 20px rgba(0, 247, 247, 0.3);
}

:deep(.vis-navigation) {
  display: none !important;
}
</style>