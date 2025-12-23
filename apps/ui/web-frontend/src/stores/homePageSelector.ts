import { ref } from 'vue'
import { defineStore } from 'pinia'
import { type PageName, defaultPage } from '@/views/home/pageMappings'

export const useHomePageSelectorStore = defineStore('homePageSelector', () => {
    const currentPage = ref<PageName>(defaultPage);

    const setCurrentPage = (page: PageName) => {
        currentPage.value = page;
    };

    return {
        currentPage,
        setCurrentPage,
    }
});