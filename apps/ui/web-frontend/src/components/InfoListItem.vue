<script setup lang="ts">
import { computed } from 'vue';
import { Edit as IconEdit } from '@icon-park/vue-next';

interface InfoListItemProps {
    name: string;
    value?: string | number | boolean | null | undefined;
    editable?: boolean;
}

const props = withDefaults(defineProps<InfoListItemProps>(), {
    editable: true,
});

// 根据 value 的值推断类型
const valueType = computed(() => {
    if (props.value === null) return 'null';
    if (props.value === undefined) return 'undefined';
    return typeof props.value;
});
</script>

<template>
<div class="info-list-item">
    <div class="name">{{ props.name }}</div>
    <div class="type">({{ valueType }})</div>
    <div class="icon-editable" v-if="props.editable"><IconEdit /></div>
    <div class="value">{{ props.value }}</div>
</div>
</template>
<style scoped>
.info-list-item {
    display: flex;
    flex-direction: row;
    align-items: baseline;
    font-size: 0.8rem;
    padding-left: 4px;
    padding-right: 4px;
    line-height: 1.5;
}

.info-list-item:hover {
    background-color: var(--color-button-hover);
}

.info-list-item .name {
    font-weight: bold;
    line-height: inherit;
}

.info-list-item .type {
    font-weight: normal;
    color: var(--color-text-secondary);
    margin-left: 4px;
    line-height: inherit;
}

.info-list-item .icon-editable {
    display: flex;
    align-items: flex-end;
    align-self: flex-end;
    color: var(--color-text-secondary);
    margin-left: 4px;
    line-height: 1;
    margin-bottom: 0.1em;
}

.info-list-item .value {
    flex: 1;
    text-align: right;
    font-weight: normal;
    line-height: inherit;
}
</style>