<script setup lang="ts">
import ResizableContainer from '@/components/ResizableContainer.vue';
import ToggleContainer from '@/components/ToggleContainer.vue';
import InfoListItem from '@/components/InfoListItem.vue';


</script>
<template>
    <ResizableContainer direction="column">
        <ToggleContainer name="NODE">
            <InfoListItem name="NAME" value="Node 1" />
            <InfoListItem name="TYPE" value="Node 2" />
        </ToggleContainer>
        <ToggleContainer name="PROJECT">
            <InfoListItem name="NAME" value="Project 1" />
            <InfoListItem name="TYPE" value="Project 2" />
        </ToggleContainer>
    </ResizableContainer>
</template>