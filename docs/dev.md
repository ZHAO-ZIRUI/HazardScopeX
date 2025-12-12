# 开发者文档

> [!IMPORTANT]
>
> 本文档仅面向开发者

**目录:**

- [基础](#基础)
- [Shared.Simulator](./dev_simulator.md)

## 基础

### ExitCode

本工程以 `ExitCode` 标记程序的运行最终结果. 只有当程序正常执行并自主退出时, 才会返回 `code: 0`. 其他更具体的 `ExitCode` 所代表的意义参见 [Exit Code 说明文件](./exit_code.md).

### Hook

本工程中大量使用了钩子 `hook` 来处理在一个 `tick()` 周期内不同对象的任务. 

钩子本质上是一个 `Callable` 的对象的列表(`list[Callable[*]]`), 在不同情境下可能有函数输入或者返回值的特殊定义. 钩子顶层是一个 `list`, 代表着钩子在执行时具有先后顺序, 并且具有一切`list` 的操作API. 本工程中的钩子在定义时被标记为 private, 如`self._hook_on_tick`, 并提供使用 `@property` 暴露的只读 public 接口. 
