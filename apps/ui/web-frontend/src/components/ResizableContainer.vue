<script setup lang="ts">
import { computed, onBeforeUnmount, ref, useSlots, watch } from 'vue';
import type { VNode } from 'vue';

interface ResizableContainerProps {
    direction: 'row' | 'column';
}

interface DragState {
    index: number;  // 当前拖动的是 index 与 index+1 之间的分隔条
    startPos: number;
    containerSize: number;
    startFirstWeight: number;
    startSecondWeight: number;
}

const props = defineProps<ResizableContainerProps>();
const slots = useSlots();
const items = computed(() => (slots.default ? slots.default() : []));

const weights = ref<number[]>([]);
const containerRef = ref<HTMLElement | null>(null);
const dragState = ref<DragState | null>(null);
const isRow = computed(() => props.direction === 'row');

const getWeight = (vnode: VNode): number => {
    const weight = (vnode.props as Record<string, unknown> | null | undefined)?.weight;
    const numeric = typeof weight === 'number' ? weight : Number(weight);
    return Number.isFinite(numeric) && numeric > 0 ? numeric : 1;
};

const clamp = (value: number, min: number, max: number): number =>
    Math.min(max, Math.max(min, value));

const onMouseMove = (event: MouseEvent) => {
    if (!dragState.value || !containerRef.value) {
        return;
    }

    const state = dragState.value;
    const currentPos = isRow.value ? event.clientX : event.clientY;
    const delta = currentPos - state.startPos;

    const totalWeight = state.startFirstWeight + state.startSecondWeight;
    if (totalWeight <= 0) {
        return;
    }

    // 将拖拽的物理距离映射到权重比例的变化
    const deltaRatio = delta / state.containerSize;
    const startRatio = state.startFirstWeight / totalWeight;
    const minRatio = 0.05;
    const maxRatio = 0.95;
    const nextRatio = clamp(startRatio + deltaRatio, minRatio, maxRatio);

    const first = totalWeight * nextRatio;
    const second = totalWeight - first;

    const idx = state.index;
    const nextWeights = [...weights.value];
    nextWeights[idx] = first;
    nextWeights[idx + 1] = second;
    weights.value = nextWeights;
};

const stopDragging = () => {
    if (!dragState.value) {
        return;
    }
    window.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('mouseup', stopDragging);
    dragState.value = null;
};

const startDragging = (index: number, event: MouseEvent) => {
    if (!containerRef.value || index < 0 || index >= weights.value.length - 1) {
        return;
    }

    const rect = containerRef.value.getBoundingClientRect();
    const containerSize = isRow.value ? rect.width : rect.height;
    if (containerSize <= 0) {
        return;
    }

    const firstVNode = items.value[index];
    const secondVNode = items.value[index + 1];
    if (!firstVNode || !secondVNode) {
        return;
    }

    dragState.value = {
        index,
        startPos: isRow.value ? event.clientX : event.clientY,
        containerSize,
        startFirstWeight: weights.value[index] ?? getWeight(firstVNode),
        startSecondWeight: weights.value[index + 1] ?? getWeight(secondVNode),
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', stopDragging);
};

watch(
    items,
    (newItems) => {
        const prev = weights.value;
        weights.value = newItems.map((vnode, index) => {
            if (prev[index] != null) {
                return prev[index]!;
            }
            return getWeight(vnode);
        });
    },
    { immediate: true }
);

onBeforeUnmount(() => {
    stopDragging();
});
</script>
<template>
    <div
        ref="containerRef"
        class="resizable-container"
        :class="props.direction"
    >
        <div
            v-for="(vnode, index) in items"
            :key="index"
            class="resizable-container-item"
            :style="{ flex: weights[index] ?? getWeight(vnode) }"
        >
            <component :is="vnode" />
            <div
                v-if="index < items.length - 1"
                class="resize-handle"
                @mousedown.prevent="startDragging(index, $event)"
            />
        </div>
    </div>
</template>
<style scoped>
@import '@/assets/base.css';

.resizable-container {
  flex: 1;
  overflow: auto;
  display: flex;
}

.resizable-container.row {
  flex-direction: row;
}

.resizable-container.column {
  flex-direction: column;
}

.resizable-container-item {
  position: relative;
}

.resizable-container-item:not(:last-child) {
  border-right: 1px solid var(--color-layout-border);
}

.resize-handle {
  position: absolute;
  top: 0;
  right: -2px;
  width: 4px;
  height: 100%;
  background-color: transparent;
  cursor: col-resize;
  transition: background-color 0.15s ease, box-shadow 0.15s ease;
}

.resizable-container.column .resize-handle {
  top: auto;
  bottom: -2px;
  left: 0;
  right: 0;
  width: 100%;
  height: 4px;
  cursor: row-resize;
}

.resize-handle:hover,
.resize-handle:active {
  background-color: var(--color-layout-border);
  box-shadow: 0 0 0 1px var(--color-layout-border);
}
</style>