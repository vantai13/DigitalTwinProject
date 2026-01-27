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
  return edges.map(edge => {
    let colorVal = '#00F7F7'
    let widthVal = 2.5
    let isDashed = false
    let shadowConfig = { enabled: false }
    
    const status = edge.status || 'unknown'
    const throughput = edge.details?.current_throughput || 0
    
    // ========================================
    // ✅ LOGIC MỚI: PHÂN BIỆT 3 TRƯỜNG HỢP
    // ========================================
    
    // CASE 1: Link thực sự DOWN (interface down)
    if (status === 'down') {
      colorVal = '#475569'
      isDashed = true
      widthVal = 1.5
      edge.label = 'DOWN'
    }
    // CASE 2: Link UP nhưng throughput = 0 (switch offline)
    else if (status === 'up' && throughput <= 0.1) {
      colorVal = '#94a3b8'  // Màu xám nhạt
      widthVal = 2
      isDashed = [5, 5]  // Nét đứt ngắn hơn
      edge.label = '0.0 Mbps (Blocked)'
      shadowConfig = { enabled: true, color: 'rgba(148, 163, 184, 0.5)', size: 15 }
    }
    // CASE 3: Link UP và có traffic
    else if (status === 'up' && throughput > 0.1) {
      edge.label = `${throughput.toFixed(1)} Mbps`
      if (edge.utilization >= 90) {
        colorVal = '#F60000'
        widthVal = 4
        shadowConfig = { enabled: true, color: 'rgba(246, 0, 0, 0.8)', size: 25 }
      } else if (edge.utilization >= 70) {
        colorVal = '#f97316'
        widthVal = 3.5
        shadowConfig = { enabled: true, color: 'rgba(249, 115, 22, 0.6)', size: 20 }
      } else {
        shadowConfig = { enabled: true, color: 'rgba(0, 247, 247, 0.5)', size: 15 }
      }
    }
    // CASE 4: Unknown/Warning
    else {
      if (status === 'warning') {
        colorVal = '#f97316'
        widthVal = 3
      }
      edge.label = `${throughput.toFixed(1)} Mbps`
    }

    return {
      ...edge,
      color: { color: colorVal, highlight: colorVal, hover: colorVal },
      width: widthVal,
      dashes: isDashed,
      shadow: shadowConfig,
      smooth: { type: 'continuous', roundness: 0.5 },
      font: { 
        color: '#00F7F7', 
        size: 11, 
        align: 'middle', 
        strokeWidth: 3, 
        strokeColor: '#0f172a' 
      }
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

    // [FIX] Xác định loại node dựa trên ID, không phải group hiện tại
    const isHost = node.id && node.id.toLowerCase().startsWith('h')
    const isSwitch = node.id && node.id.toLowerCase().startsWith('s')

    // [FIX] Xác định group dựa trên loại node (isHost/isSwitch) và status
    if (status === 'offline') {
      if (isHost) {
        finalGroup = 'host-offline'
      } else if (isSwitch) {
        finalGroup = 'switch-offline'
      }
    } else if (status === 'high-load') {
      // [FIX] Quan trọng: Dựa vào isHost, không phải node.group
      if (isHost) {
        finalGroup = 'host-high-load'
      } else if (isSwitch) {
        finalGroup = 'switch-high-load'
      }
    } else {
      // [FIX] Đảm bảo group đúng với loại node
      if (isHost) {
        finalGroup = 'host'
      } else if (isSwitch) {
        finalGroup = 'switch'
      }
    }

    return {
      ...node,
      group: finalGroup,
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