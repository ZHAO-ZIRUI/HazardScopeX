import type { Component } from 'vue';
import FlowPage from '@/views/home/flow/FlowPage.vue';
import FlowSidebarL from '@/views/home/flow/FlowSidebarL.vue';
import FlowSidebarR from '@/views/home/flow/FlowSidebarR.vue';
import ExperimentPage from '@/views/home/experiment/ExperimentPage.vue';
import ExperimentSidebarL from '@/views/home/experiment/ExperimentSidebarL.vue';
import ExperimentSidebarR from '@/views/home/experiment/ExperimentSidebarR.vue';
import DatasetPage from '@/views/home/dataset/DatasetPage.vue';
import DatasetSidebarL from '@/views/home/dataset/DatasetSidebarL.vue';
import DatasetSidebarR from '@/views/home/dataset/DatasetSidebarR.vue';
import FactorsPage from '@/views/home/factors/FactorsPage.vue';
import FactorsSidebarL from '@/views/home/factors/FactorsSidebarL.vue';
import FactorsSidebarR from '@/views/home/factors/FactorsSidebarR.vue';
import RunnerPage from '@/views/home/runner/RunnerPage.vue';
import RunnerSidebarL from '@/views/home/runner/RunnerSidebarL.vue';
import RunnerSidebarR from '@/views/home/runner/RunnerSidebarR.vue';
import SettingPage from '@/views/home/setting/SettingPage.vue';
import SettingSidebarL from '@/views/home/setting/SettingSidebarL.vue';
import SettingSidebarR from '@/views/home/setting/SettingSidebarR.vue';

export type PageName = 'flow' | 'experiment' | 'dataset' | 'factors' | 'runner' | 'setting';

export type IconType = 'IconAssemblyLine' | 'IconExperiment' | 'IconData' | 'IconRoadCone' | 'IconServer' | 'IconSetting';

// 图标与页面的映射
export const iconToPageMap: Record<IconType, PageName> = {
  'IconAssemblyLine': 'flow',
  'IconExperiment': 'experiment',
  'IconData': 'dataset',
  'IconRoadCone': 'factors',
  'IconServer': 'runner',
  'IconSetting': 'setting',
};

// 页面与页面组件的映射
export const pageComponents: Record<PageName, Component> = {
  'flow': FlowPage,
  'experiment': ExperimentPage,
  'dataset': DatasetPage,
  'factors': FactorsPage,
  'runner': RunnerPage,
  'setting': SettingPage,
};

// 页面与左侧边栏组件的映射
export const sidebarLComponents: Record<PageName, Component> = {
  'flow': FlowSidebarL,
  'experiment': ExperimentSidebarL,
  'dataset': DatasetSidebarL,
  'factors': FactorsSidebarL,
  'runner': RunnerSidebarL,
  'setting': SettingSidebarL,
};

// 页面与右侧边栏组件的映射
export const sidebarRComponents: Record<PageName, Component> = {
  'flow': FlowSidebarR,
  'experiment': ExperimentSidebarR,
  'dataset': DatasetSidebarR,
  'factors': FactorsSidebarR,
  'runner': RunnerSidebarR,
  'setting': SettingSidebarR,
};

// 默认页面
export const defaultPage: PageName = 'flow';

