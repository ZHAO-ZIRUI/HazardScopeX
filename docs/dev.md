# 开发者文档

> [!IMPORTANT]
>
> 本文档仅面向开发者

## CarlaContext

```sh
./shared/simulator/carla_context.py
```

`CarlaContext` 用于管理 CARLA 仿真过程的完整生命周期, 提供以下功能:

- CARLA 服务端的拉起、终止、存活检查
- CARLA 仿真过程中的 `tick()` 控制, 包括阻塞、等待、持续运行
- CARLA 仿真中常用对象的别名快捷访问方法
- 提供多个子服务的单例实例

`CarlaContext` 接收配置文件启动，如果不需要特别指定启动配置文件, 可以使用以下代码最简启动:

```python
with CarlaContext() as context:
    context.spin()
```

### heavy_operation

`CarlaContext.heavy_operation()` 用于标记一个可能会长时间阻塞 CARLA 服务端且会导致客户端短暂无法响应的操作. `heavy_operation()` 使用了 `contextmanager`, 

