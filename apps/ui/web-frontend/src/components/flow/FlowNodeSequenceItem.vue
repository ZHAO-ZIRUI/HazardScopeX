<script setup lang="ts">
import { Position, Handle } from '@vue-flow/core';
import { RightOne as IconRightOne, DiamondThree as IconDiamondThree } from '@icon-park/vue-next';
import type { FlowNodeItemProps } from './flow';

const props = withDefaults(defineProps<FlowNodeItemProps>(), {
    hasInput: true,
    hasOutput: true,
});
</script>
<template>
    <div class="flow-node-item">
        <div class="sequence-content">
            <IconRightOne
                v-if="props.hasInput"
                class="sequence-icon"
                theme="filled"
                size="22"
            />
            <IconDiamondThree
                v-if="!props.hasInput"
                class="sequence-icon"
                theme="filled"
                size="14"
            />
            <div class="sequence-line"></div>
            <IconRightOne
                v-if="props.hasOutput"
                class="sequence-icon"
                theme="filled"
                size="22"
            />
            <IconDiamondThree
                v-if="!props.hasOutput"
                class="sequence-icon"
                theme="filled"
                size="14"
            />
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

.sequence-content {
    display: flex;
    align-items: center;
}

.sequence-line {
    flex: 1;
    height: 1px;
    background-color: var(--color-text);
    padding: 0px;
}

.sequence-icon {
    display: inline-flex;
}
</style>