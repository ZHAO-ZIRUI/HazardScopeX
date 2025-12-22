<script setup lang="ts">
import { computed, onBeforeUnmount, provide, ref, useSlots, watch } from 'vue';
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

// 常量定义
const COLLAPSED_WEIGHT = 0.001; // 折叠时的最小权重（只保留标题栏）
const MIN_RATIO = 0.05; // 拖拽时的最小比例
const MAX_RATIO = 0.95; // 拖拽时的最大比例
const TRANSITION_DURATION = '0.2s'; // 过渡动画时长

// 状态管理
const weights = ref<number[]>([]);
const containerRef = ref<HTMLElement | null>(null);
const dragState = ref<DragState | null>(null);
const isRow = computed(() => props.direction === 'row');

// 跟踪每个子组件的折叠状态和保存的权重
const toggleStates = ref<Map<number, boolean>>(new Map());
const savedWeights = ref<Map<number, number>>(new Map());
let nextIndex = 0;

/**
 * 从 VNode 中获取权重值
 */
const getWeight = (vnode: VNode): number => {
    const weight = (vnode.props as Record<string, unknown> | null | undefined)?.weight;
    const numeric = typeof weight === 'number' ? weight : Number(weight);
    return Number.isFinite(numeric) && numeric > 0 ? numeric : 1;
};

/**
 * 将值限制在指定范围内
 */
const clamp = (value: number, min: number, max: number): number =>
    Math.min(max, Math.max(min, value));

/**
 * 计算合理的初始权重
 */
const calculateReasonableWeight = (totalItems: number): number => {
    return totalItems > 0 ? Math.max(1, 3 / totalItems) : 1;
};

/**
 * 注册子组件的折叠状态
 */
const registerToggleState = (index: number, isOpen: boolean) => {
    const wasOpen = toggleStates.value.get(index) ?? true;
    const isExpanding = !wasOpen && isOpen;
    
    toggleStates.value.set(index, isOpen);
    
    // 如果是从折叠状态展开，且没有保存的权重，设置一个合理的初始权重
    if (isExpanding && !savedWeights.value.has(index)) {
        const reasonableWeight = calculateReasonableWeight(items.value.length);
        savedWeights.value.set(index, reasonableWeight);
    }
    
    updateWeightsForToggle();
};

/**
 * 获取容器的基础权重（优先使用保存的权重）
 */
const getBaseWeight = (
    index: number,
    reasonableInitialWeight: number
): number => {
    const savedWeight = savedWeights.value.get(index);
    const currentWeight = weights.value[index];
    
    if (savedWeight != null) {
        return savedWeight;
    }
    
    if (currentWeight == null || currentWeight <= COLLAPSED_WEIGHT) {
        // 当前权重是折叠权重或不存在，使用合理的初始权重并保存
        const weight = reasonableInitialWeight;
        if (!savedWeights.value.has(index)) {
            savedWeights.value.set(index, weight);
        }
        return weight;
    }
    
    return currentWeight;
};

/**
 * 根据折叠状态更新权重（类似 VSCode 的行为）
 */
const updateWeightsForToggle = () => {
    const openIndices: number[] = [];
    const closedIndices: number[] = [];
    
    // 收集所有展开和折叠的索引
    items.value.forEach((_, index) => {
        const isOpen = toggleStates.value.get(index) ?? true;
        (isOpen ? openIndices : closedIndices).push(index);
    });
    
    const newWeights = [...weights.value];
    const reasonableInitialWeight = calculateReasonableWeight(items.value.length);
    
    // 处理折叠的容器：保存当前权重并设置为折叠权重
    closedIndices.forEach((index) => {
        const currentWeight = weights.value[index];
        if (currentWeight != null && currentWeight > COLLAPSED_WEIGHT) {
            if (!savedWeights.value.has(index)) {
                savedWeights.value.set(index, currentWeight);
            }
        }
        newWeights[index] = COLLAPSED_WEIGHT;
    });
    
    // 处理展开的容器
    if (openIndices.length === 0) {
        return;
    }
    
    const totalCollapsedWeight = closedIndices.length * COLLAPSED_WEIGHT;
    const totalAvailable = 1 - totalCollapsedWeight;
    
    // 计算展开容器的总权重
    const baseWeights = new Map<number, number>();
    let totalOpenWeight = 0;
    
    openIndices.forEach((index) => {
        const weight = getBaseWeight(index, reasonableInitialWeight);
        baseWeights.set(index, weight);
        totalOpenWeight += weight;
    });
    
    if (totalOpenWeight <= 0) {
        return;
    }
    
    // 重新分配权重：展开的容器按比例分配剩余空间
    openIndices.forEach((index) => {
        const baseWeight = baseWeights.get(index)!;
        const ratio = baseWeight / totalOpenWeight;
        newWeights[index] = totalAvailable * ratio;
    });
    
    weights.value = newWeights;
};

// 提供注册方法给子组件
provide('registerToggleState', (isOpen: boolean) => {
    const index = nextIndex++;
    registerToggleState(index, isOpen);
    return index;
});

// 提供更新方法给子组件
provide('updateToggleState', (index: number, isOpen: boolean) => {
    registerToggleState(index, isOpen);
});

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
    const nextRatio = clamp(startRatio + deltaRatio, MIN_RATIO, MAX_RATIO);

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
        // 重置索引计数器
        nextIndex = 0;
        
        // 初始化权重
        const prev = weights.value;
        weights.value = newItems.map((vnode, index) => {
            if (prev[index] != null) {
                return prev[index]!;
            }
            return getWeight(vnode);
        });
        
        // 初始化时，所有容器默认展开
        newItems.forEach((_, index) => {
            if (!toggleStates.value.has(index)) {
                toggleStates.value.set(index, true);
            }
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
            :style="{ 
                flex: weights[index] ?? getWeight(vnode),
                transition: dragState ? 'none' : `flex ${TRANSITION_DURATION} ease-out`
            }"
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
  height: 100%;
}

.resizable-container-item {
  position: relative;
  /* 保证折叠时至少能显示一行标题栏 */
  min-height: 24px;
  min-width: 0;
  overflow: hidden;
}

.resizable-container.column .resizable-container-item {
  display: flex;
  flex-direction: column;
}

.resizable-container.column .resizable-container-item:not(:last-child) {
  border-right: none;
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