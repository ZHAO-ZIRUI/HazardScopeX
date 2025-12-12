# 开发者文档

> [!IMPORTANT]
>
> 本文档仅面向开发者

## 基础

### ExitCode

本工程以 `ExitCode` 标记程序的运行最终结果. 只有当程序正常执行并自主退出时, 才会返回 `code: 0`. 其他更具体的 `ExitCode` 所代表的意义参见 [Exit Code 说明文件](./exit_code.md).

### Hook

本工程中大量使用了钩子 `hook` 来处理在一个 `tick()` 周期内不同对象的任务. 

钩子本质上是一个 `Callable` 的对象的列表(`list[Callable[*]]`), 在不同情境下可能有函数输入或者返回值的特殊定义. 钩子顶层是一个 `list`, 代表着钩子在执行时具有先后顺序, 并且具有一切`list` 的操作API. 本工程中的钩子在定义时被标记为 private, 如`self._hook_on_tick`, 并提供使用 `@property` 暴露的只读 public 接口. 

## Simulator

### CarlaContext

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

#### heavy_operation

该方法用于标记一个可能会长时间阻塞 CARLA 服务端且会导致客户端短暂无法响应的操作. `heavy_operation()` 使用了 `contextmanager`, 因此可以简单的通过以下方式使用:

```python
with context.heavy_operation():
    some_heavy_operation()
```

目前, `CarlaContext.change_map()` 内置使用了 `CarlaContext.heavy_operation()`.


#### tick

`CarlaContext.tick()` 在原有 CARLA API `carla.world.tick()` 的基础上, 增加了以下功能:

- 在 `CarlaContext` 中的全局 Tick 阻塞控制, 使用 `CarlaTickBlocker` 确保在每一个 Tick 周期内的操作都按照计划完成, 避免因为 CARLA 传感器的 `listen()` 函数回调值在 `tick()` 后的不可控时间被调用导致的错帧等问题
- 在 `CarlaContext` 内部的全局钩子 `hook_on_tick` 的调用

> [!NOTE]
> 
> 建议在外部程序中使用 `CarlaContext.wait_seconds(1, no_log=True)` 来代替 `CarlaContext.tick()`. 可以防止在短时间内连续请求服务端进行 `tick()` 操作

#### wait_seconds & wait_ticks

等待操作, 等待指定的秒数或者等待几次 tick. 本项目中, `CARLA` 服务端必定工作在同步模式下, 因此等待操作会主动调用 `CarlaContext.tick()` 来 Tick 服务端.

该方法会动态计算需要等待的时间, 以使得服务端的 Tick 间隔尽可能贴近 `self.configs.context.runtime_sync_mode_fps` 的设定值.

操作提供了 3 个可选的布尔参数:
- `force`: 内含的 `CarlaContext.tick()` 操作会跳过阻塞检查
- `no_log`: 不打印日志
- `raise_interrupted`: 异常 `KeyboardInterrupt` 将会在打印日志后再次抛出, 由上级程序处理后续操作


#### spin

`CarlaContext.spin()` 操作属于等待的一种, 但是会一直持续并阻塞主程序, 因此该操作一般在最后进行:

```python
with CarlaContext() as context:
    do_something()
    ...
    context.spin()

# PROGRAM EXIT
```

特别的, `CarlaContext.spin()` 操作会处理 `KeyboardInterrupt` 并直接以 `code:100` 退出, 因此在其后的代码并不会执行.

