<script setup lang="ts">
import FlowNodeItem from './FlowNodeItem.vue';
import FlowNodeSequenceItem from './FlowNodeSequenceItem.vue';
import { type FlowNodeProps } from './flow';
import { DatabaseCode as IconDatabaseCode } from '@icon-park/vue-next';

const props = defineProps<FlowNodeProps>();
</script>
<template>
    <div class="flow-node">
        <div class="flow-node header">
            <IconDatabaseCode class="flow-node-icon" size="16" />
            <span class="flow-node-title">{{ props.name }}</span>
        </div>
        <div class="flow-node body">
            <FlowNodeSequenceItem :parent-id="props.id" self-id="0"/>
            <FlowNodeItem :parent-id="props.id" self-id="1" name="Item 1" />
            <FlowNodeItem :parent-id="props.id" self-id="2" name="Item 2" />
            <FlowNodeItem :parent-id="props.id" self-id="3" name="Item 3" />
        </div>
    </div>
</template>
<style scoped>
@import '@/assets/flow.css';
</style>