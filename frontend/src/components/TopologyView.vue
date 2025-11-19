<template>
  <div class="topology-view">
    <h3>NETWORK TOPOLOGY</h3>
    <div class="diagram-container" ref="networkContainer"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { Network } from 'vis-network/standalone'
import 'vis-network/styles/vis-network.css'
import iconHost from '@/assets/icons/laptop.png'
import iconSwitch from '@/assets/icons/switch.png'

const props = defineProps(['graphData'])
const emit = defineEmits(['node-selected', 'edge-selected', 'selection-cleared'])

const networkContainer = ref(null) // div chứa sơ đồ
const networkInstance = ref(null) // đối tượng vis-network

//  Dùng computed để trigger re-render
const graphDataString = computed(() => JSON.stringify(props.graphData))

function processEdges(edges) {
  if (!Array.isArray(edges)) return []

  return edges.map(edge => {
    // Mặc định (status = 'up')
    let colorVal = '#00F7F7'   // Cyan
    let widthVal = 2.5
    let isDashed = false
    let shadowConfig = { enabled: false }
    
    // Lấy status từ Backend gửi xuống
    // (Lưu ý: data từ backend có thể nằm trong edge hoặc edge.details tùy cách bạn gán ở App.vue)
    const status = edge.status || edge.details?.status || 'unknown'
    const utilization = edge.utilization || 0
    if (utilization > 1 && (status === 'down' || status === 'offline' || status === 'unknown')) {
        status = 'up'; 
    }

    // --- [LOGIC HIỂN THỊ DỰA TRÊN TRẠNG THÁI] ---
    switch (status) {
      case 'down':
      case 'offline':
        colorVal = '#475569' // Gray
        isDashed = true
        widthVal = 1.5
        break
        
      case 'high-load':
        colorVal = '#F60000' // Red - Nguy hiểm
        widthVal = 4
        shadowConfig = { enabled: true, color: 'rgba(246, 0, 0, 0.8)', size: 25 }
        break
        
      case 'warning':
        colorVal = '#f97316' // Orange - Cảnh báo
        widthVal = 3.5
        shadowConfig = { enabled: true, color: 'rgba(249, 115, 22, 0.6)', size: 20 }
        break
        
      case 'up':
      default:
        // Nếu đang UP mà có lưu lượng > 0 thì cho phát sáng nhẹ cho đẹp
        if (utilization > 0) {
           shadowConfig = { enabled: true, color: 'rgba(0, 247, 247, 0.5)', size: 15 }
        }
        break
    }

    // Animation arrows (Giữ nguyên logic hiển thị mũi tên khi có traffic)
    let arrowsConfig = { to: { enabled: false } }
    if (status !== 'down' && utilization > 1) {
      let arrowSpeed = 1
      if (status === 'high-load') arrowSpeed = 2.5
      else if (status === 'warning') arrowSpeed = 1.5
      
      arrowsConfig = {
        to: { enabled: true, type: 'arrow', scaleFactor: 0.8 },
        middle: { enabled: true, type: 'arrow', scaleFactor: 0.6 }
      }
    }

    return {
      ...edge,
      color: {
        color: colorVal,
        highlight: colorVal,
        hover: colorVal
      },
      width: widthVal,
      arrows: arrowsConfig,
      dashes: isDashed,
      shadow: shadowConfig,
      // ... (giữ nguyên các thuộc tính font/smooth)
      smooth: { type: 'continuous', roundness: 0.5 },
      font: { color: '#00F7F7', size: 11, align: 'middle', strokeWidth: 3, strokeColor: '#0f172a' }
    }
  })
}

function processNodes(nodes) {
  if (!Array.isArray(nodes)) {
    console.error("processNodes: nodes không phải array", nodes)
    return []
  }

  return nodes.map(node => {
    const status = node.details?.status
    let finalGroup = node.group

    // Xác định group dựa trên status
    if (status === 'offline') {
      finalGroup = node.group === 'host' ? 'host-offline' : 'switch-offline'
    } else if (status === 'high-load') {
      finalGroup = node.group === 'host' ? 'host-high-load' : 'switch-high-load'
    }

    return {
      ...node,
      group: finalGroup,
      // Add tooltip
      title: `${node.id}\nStatus: ${status || 'unknown'}\n${
        node.details?.cpu_utilization 
          ? `CPU: ${node.details.cpu_utilization}%` 
          : ''
      }`
    }
  })
}

function initializeNetwork() {
  if (!networkContainer.value || !props.graphData) {
    console.error("TopologyView: Container hoặc graphData chưa sẵn sàng")
    return
  }

  const processedEdges = processEdges(props.graphData.edges)
  const processedNodes = processNodes(props.graphData.nodes)

  console.log(' Initializing network with:', {
    nodes: processedNodes.length,
    edges: processedEdges.length
  })

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
      selectionWidth: 4
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
          background: '#0f172a'
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
          highlight: { border: '#F60000', background: '#1e293b' }
        },
        shadow: {
          enabled: true,
          color: 'rgba(246, 0, 0, 0.8)',
          size: 25
        }
      },
      switch: {
        shape: 'image',
        image: iconSwitch,
        color: {
          border: '#f97316',
          background: '#0f172a',
          highlight: { border: '#f97316', background: '#1e293b' }
        },
        shadow: {
          enabled: true,
          color: 'rgba(249, 115, 22, 0.8)',
          size: 25
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
          background: '#0f172a'
        },
        shadow: {
          enabled: true,
          color: 'rgba(246, 0, 0, 0.8)',
          size: 25
        }
      }
    }
  }

  try {
    networkInstance.value = new Network(networkContainer.value, data, options)

    // Event handlers
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

    console.log("Vis.js network initialized")
  } catch (error) {
    console.error(" Error initializing Vis.js:", error)
  }
}

onMounted(() => {
  initializeNetwork()
})

//  Watch graphDataString
watch(graphDataString, (newVal, oldVal) => {
  if (newVal !== oldVal && networkInstance.value) {
    console.log(' Updating network visualization...')
    
    const processedEdges = processEdges(props.graphData.edges)
    const processedNodes = processNodes(props.graphData.nodes)

    try {
      networkInstance.value.body.data.nodes.update(processedNodes)
      networkInstance.value.body.data.edges.update(processedEdges)
    } catch (error) {
      console.error(' Error updating network:', error)
    }
  }
})
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