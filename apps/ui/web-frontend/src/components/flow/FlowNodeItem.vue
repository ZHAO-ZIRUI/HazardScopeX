<script setup lang="ts">
import { Position, Handle } from '@vue-flow/core';
import { type FlowNodeItemProps } from './flow';

const props = withDefaults(defineProps<FlowNodeItemProps>(), {
    hasInput: true,
    hasOutput: true,
});
</script>
<template>
    <div class="flow-node-item">
        <div class="flow-node-item-content">
            <div class="flow-node-item name">
                {{ props.name }}
            </div>
        </div>
        <Handle
            v-if="props.hasInput"
            :id="`${props.parentId}-${props.selfId}-left`" 
            type="source" 
            :position="Position.Left" 
        />
        <Handle 
            v-if="props.hasOutput"
            :id="`${props.parentId}-${props.selfId}-right`" 
            type="target" 
            :position="Position.Right"
        />
    </div>
</template>

<style scoped>
@import '@/assets/flow.css';
</style>