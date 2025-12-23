<script setup lang="ts">
    // @ts-nocheck
    import { ref } from 'vue'
    import type { Node, Edge, Connection } from '@vue-flow/core'  
    import { VueFlow, addEdge } from '@vue-flow/core'
    import { Background } from '@vue-flow/background'
    import { MiniMap } from '@vue-flow/minimap'
    
    // these components are only shown as examples of how to use a custom node or edge
    // you can find many examples of how to create these custom components in the examples page of the docs
    import SpecialNode from '@/components/SpecialNode.vue'
    import SpecialEdge from '@/components/SpecialEdge.vue'
    import ExampleFlowNode from '@/components/flow/ExampleFlowNode.vue'
    
    const VueFlowAny = VueFlow as any

    // 节点配置
    const nodes = ref<Node[]>([
      // an input node, specified by using `type: 'input'`
      {
        id: '1',
        type: 'input',
        position: { x: 250, y: 5 },
        // all nodes can have a data object containing any data you want to pass to the node
        // a label can property can be used for default nodes
        data: { label: 'Node 1' },
      },
      {
        id: '2',
        type: 'example-flow-node',
        position: { x: 250, y: 250 },
        data: { label: 'Node 2' },
      },
    ])
    
    // 边配置（使用 ref 以支持交互连线）
    const edges = ref<Edge[]>([])

    // 处理连接事件，基于 Vue Flow 默认逻辑增加边
    const onConnect = (connection: Connection) => {
      edges.value = addEdge(connection, edges.value)
    }
    </script>
    
    <template>
      <VueFlowAny
        :nodes="nodes"
        :edges="edges as any"
        class="flow-page"
        @connect="onConnect"
      >
        <!-- bind your custom node type to a component by using slots, slot names are always `node-<type>` -->
        <template #node-example-flow-node="exampleFlowNodeProps">
          <ExampleFlowNode name="Exmaple NODE" id="0" />
        </template>
    
        <!-- bind your custom edge type to a component by using slots, slot names are always `edge-<type>` -->
        <Background />
      </VueFlowAny>
    </template>
    
    <style scoped>
    .flow-page {
      background-color: var(--color-flow-background);
    }
    </style>
    <style>
    @import '@vue-flow/core/dist/style.css';
    @import '@vue-flow/core/dist/theme-default.css';
    </style>