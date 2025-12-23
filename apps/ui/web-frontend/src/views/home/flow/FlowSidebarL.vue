<script setup lang="ts">
import ResizableContainer from '@/components/ResizableContainer.vue';
import ToggleContainer from '@/components/ToggleContainer.vue';
import InfoListItem from '@/components/InfoListItem.vue';
</script>
<template>
    <ResizableContainer direction="column">
        <ToggleContainer name="NODE LIST">
            <InfoListItem name="NAME" value="Item 1" />
            <InfoListItem name="TYPE" value="Item 2" />
        </ToggleContainer>
    </ResizableContainer>
</template>