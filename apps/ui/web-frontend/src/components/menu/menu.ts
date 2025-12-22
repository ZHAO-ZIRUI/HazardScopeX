import type { Ref } from 'vue';

export type MenuGroupId = symbol;

export interface MenuContext {
  activeGroupId: Ref<MenuGroupId | null>;
  toggleGroup: (id: MenuGroupId) => void;
  closeAll: () => void;
}