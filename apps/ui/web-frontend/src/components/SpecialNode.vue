<script setup lang="ts">
  import { computed, useSlots } from 'vue'
  import { Position, Handle } from '@vue-flow/core'
  import type { NodeProps } from '@vue-flow/core'
    
  const props = defineProps<NodeProps>()
  const slots = useSlots()
  
  // 从 data 中获取子节点列表，如果没有则使用空数组
  const children = computed(() => props.data?.children || [])
</script>

<template>
  <div class="special-node">
    <!-- 节点标题/内容 -->
    <div class="special-node-header">
      {{ data.label }}
    </div>
    
    <!-- 子节点列表容器 -->
    <div v-if="children.length > 0 || slots.children" class="special-node-children">
      <!-- 通过插槽方式渲染子节点 -->
      <slot name="children">
        <!-- 如果没有插槽，则通过 data.children 渲染子节点 -->
        <div
          v-for="(child, index) in children"
          :key="child.id || index"
          class="special-node-child"
        >
          <div class="special-node-child-content">
            {{ child.label || child }}
          </div>
          <!-- 左侧 Handle -->
          <Handle :id="`${props.id}-child-${index}-left`" type="source" :position="Position.Left" />
          <Handle :id="`${props.id}-child-${index}-left-target`" type="target" :position="Position.Left" />
          <!-- 右侧 Handle -->
          <Handle :id="`${props.id}-child-${index}-right`" type="source" :position="Position.Right" />
          <Handle :id="`${props.id}-child-${index}-right-target`" type="target" :position="Position.Right" />
        </div>
      </slot>
    </div>
    
    <!-- 父节点的 Handle -->
    <Handle id="left" type="source" :position="Position.Left" />
    <Handle id="left-target" type="target" :position="Position.Left" />
    <Handle id="right" type="source" :position="Position.Right" />
    <Handle id="right-target" type="target" :position="Position.Right" />
  </div>
</template>

<style scoped>
.special-node {
  position: relative;
  min-width: 200px;
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 12px;
}

.special-node-header {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
  text-align: center;
}

.special-node-children {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.special-node-child {
  position: relative;
  padding: 6px 12px;
  background-color: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  min-width: 120px;
  text-align: center;
}

.special-node-child-content {
  font-size: 13px;
  color: #666;
}
</style>