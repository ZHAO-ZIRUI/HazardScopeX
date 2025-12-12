# HazardScopeX

本项目是面向自动驾驶仿真的因子注入框架, 基于 [CARLA仿真器](https://github.com/carla-simulator/carla) 开发, 提供了以下主要功能:

- 高性能的仿真车辆数据的输出. 
- 支持传感器复现的仿真录制与回放功能.
- 经过工程验证的数据集导出功能.
- 完整且灵活的仿真流程设计.
- 完善的因子定义、注入与评估系统.

## 安装

### Python 环境

本项目使用 `uv` 管理项目依赖, 首先需要安装 `uv`, 如果已经安装可以跳过该步骤.

```sh
pip install uv
```

在安装 `uv` 后, 使用下列命令创建虚拟环境并同步依赖

```sh
uv sync
```

> [!TIP]
> 
> 我们推荐使用 ROS2 作为通信中间件, 并使用 `rviz2` 进行可视化调试.

### 程序配置

在开始运行前, 你需要设置程序的配置文件

1. 拷贝 `config.template.yaml` 并重命名为 `config.yaml`
2. 根据您的操作系统, 确定你的 CARLA 服务端执行绝对路径, 例如: `/some/path/CarlaUE4.sh`
3. 更新 `config.yaml`
    ```yaml
    context:
        server:
        ...
            self_managed:
                enabled: true
                exe_path: "/some/path/CarlaUE4.sh" # UPDATE HERE
    ```

> [!TIP]
> 
> 如果您更希望独立运行 CARLA 服务端, 可以设置 `self_managed: enabled: false`

## 运行

所有的具体程序均放置在 `./apps` 文件夹下, 你可以通过以下命令运行简单的 Demo

```sh
uv run python ./apps/demo/simple_server.py
```

你可以在 `./apps/demo` 中找到包含完整注释的示例代码

## 结构

本项目的顶层结构如下文所示, 具体的结构设计可参考 [开发](./docs/dev.md) 文档

```sh
.
├── README.md               # 本文件
├── apps                    # 具体任务的执行文件
├── config.template.yaml    # 示例配置文件
├── docs                    # 文档
├── export                  # 输出文件夹, 用于保存数据集
├── pyproject.toml          # UV 的项目配置文件
├── recorders               # 输出文件夹, 用于保存录制与回放
├── shared                  # 基础共享库
├── test                    # 单元测试
├── tmp                     # 临时文件夹
└── uv.lock                 # UV 的依赖文件
```

## 关于

本项目由南方科技大学计算机科学与工程系郝祁课题组, 南方科技大学斯发基斯可信自主系统研究院自动驾驶中心维护.

你可以通过 Github 邮件联系作者.
