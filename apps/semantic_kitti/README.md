# Semantic KITTI Dataset Dump

导出为 Semantic KITTI 数据集的示例程序

## Structure

```
./apps/semantic_kitti
├── draw_calib.py                   # 绘制标定结果
├── draw_pose.py                    # 绘制路径
├── README.md                       # 本文件
└── simple_semantic_kitti_dump.py   # 主程序样例
```

## Run

运行前请确保以下事项就绪:
- [ ] UV 环境已经正确配置
- [ ] config.yaml 已经正确配置

```
uv run python ./apps/semantic_kitti/simple_semantic_kitti_dump.py 
```

数据集会储存在 `<PROJECT_ROOT>/export` 目录下

> ⚠️ **WARN**
> 
> 默认情况下, Context 工作在宿主模式下(`use_external_server: false`), 该程序会主动拉起一个 CARLA 服务端并管理其生命周期, 你仅需要将 `config.template.yaml` 复制并重命名为 `config.yaml`, 
> 并手动修改 `exe_path` 即可正常使用.
