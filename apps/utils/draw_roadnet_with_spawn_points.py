import argparse
import matplotlib.pyplot as plt
from shared.simulator import CarlaContext
from shared.utils import Config, Logging


def draw_roadnet_with_spawn_points(context: CarlaContext, output_path: str):
    """
    绘制CARLA路网和SpawnPoint的俯视图
    
    Args:
        context: CARLA上下文
        output_path: 输出文件路径
    """
    logger = Logging().get_logger('DrawRoadnet')
    
    # 获取地图和spawn points
    carla_map = context.world.get_map()
    spawn_points = context.spawn_points
    
    logger.info(f'Found {len(spawn_points)} spawn points')
    
    # 先收集所有spawn points的坐标，确保它们都被包含在视图中
    spawn_points_coords = []
    for idx, spawn_point in enumerate(spawn_points):
        spawn_points_coords.append({
            'idx': idx,
            'x': spawn_point.location.x,
            'y': spawn_point.location.y
        })
    
    logger.info(f'Collected coordinates for {len(spawn_points_coords)} spawn points')
    
    # 获取路网拓扑
    topology = carla_map.get_topology()
    logger.info(f'Found {len(topology)} road segments')
    
    # 创建图形
    fig, ax = plt.subplots(figsize=(20, 20))
    
    # 收集所有坐标用于计算边界（先添加spawn points，确保它们被包含）
    all_x = [sp['x'] for sp in spawn_points_coords]
    all_y = [sp['y'] for sp in spawn_points_coords]
    
    # 采样距离（米），用于离散化道路
    sampling_resolution = 1.0
    
    # 绘制路网
    for waypoint_pair in topology:
        # 获取起点和终点waypoint
        start_waypoint = waypoint_pair[0]
        end_waypoint = waypoint_pair[1]
        
        # 沿着道路采样多个点
        waypoint_path = []
        current_waypoint = start_waypoint
        
        # 计算起点到终点的距离
        start_loc = start_waypoint.transform.location
        end_loc = end_waypoint.transform.location
        distance_to_end = start_loc.distance(end_loc)
        
        # 沿着道路采样，直到接近终点
        max_iterations = int(distance_to_end / sampling_resolution) + 20  # 防止无限循环
        iteration = 0
        visited_waypoints = set()  # 防止循环
        
        while iteration < max_iterations:
            waypoint_path.append(current_waypoint)
            current_loc = current_waypoint.transform.location
            
            # 如果已经接近终点，停止采样
            if current_loc.distance(end_loc) < sampling_resolution * 1.5:
                waypoint_path.append(end_waypoint)
                break
            
            # 获取下一个waypoint
            next_waypoints = current_waypoint.next(sampling_resolution)
            if not next_waypoints:
                # 如果没有下一个waypoint，直接连接到终点
                waypoint_path.append(end_waypoint)
                break
            
            # 过滤掉已访问的waypoint，防止循环
            unvisited_waypoints = [wp for wp in next_waypoints if id(wp) not in visited_waypoints]
            if not unvisited_waypoints:
                # 如果所有waypoint都已访问，选择距离终点最近的
                unvisited_waypoints = next_waypoints
            
            # 选择距离终点最近的waypoint（如果有多个选择）
            current_waypoint = min(unvisited_waypoints, key=lambda wp: wp.transform.location.distance(end_loc))
            visited_waypoints.add(id(current_waypoint))
            iteration += 1
        
        # 提取所有采样点的坐标
        path_x = [wp.transform.location.x for wp in waypoint_path]
        path_y = [wp.transform.location.y for wp in waypoint_path]
        
        # 收集坐标
        all_x.extend(path_x)
        all_y.extend(path_y)
        
        # 绘制离散化的道路段
        ax.plot(
            path_x,
            path_y,
            'b-',
            linewidth=1.5,
            alpha=0.6,
            label='Road Network' if waypoint_pair == topology[0] else ''
        )
    
    # 绘制spawn points并标注idx（确保所有spawn points都被绘制）
    drawn_spawn_count = 0
    for spawn_info in spawn_points_coords:
        idx = spawn_info['idx']
        spawn_x = spawn_info['x']
        spawn_y = spawn_info['y']
        
        # 绘制spawn point标记
        ax.plot(
            spawn_x,
            spawn_y,
            'ro',
            markersize=8,
            markeredgecolor='darkred',
            markeredgewidth=1.5,
            label='Spawn Points' if idx == 0 else ''
        )
        
        # 标注idx
        ax.annotate(
            str(idx),
            (spawn_x, spawn_y),
            xytext=(5, 5),
            textcoords='offset points',
            fontsize=8,
            fontweight='bold',
            color='red',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='red', linewidth=1)
        )
        drawn_spawn_count += 1
    
    logger.info(f'Drawn {drawn_spawn_count} spawn points (expected {len(spawn_points)})')
    
    # 验证所有spawn points都被绘制
    if drawn_spawn_count != len(spawn_points):
        logger.warning(f'Mismatch: drawn {drawn_spawn_count} spawn points but expected {len(spawn_points)}')
    
    # 设置坐标轴（确保所有spawn points都在视图内）
    if all_x and all_y:
        # 计算边界，添加一些边距
        margin = 50
        min_x = min(all_x)
        max_x = max(all_x)
        min_y = min(all_y)
        max_y = max(all_y)
        
        # 验证spawn points都在边界内
        spawn_x_coords = [sp['x'] for sp in spawn_points_coords]
        spawn_y_coords = [sp['y'] for sp in spawn_points_coords]
        
        if spawn_x_coords and spawn_y_coords:
            spawn_min_x = min(spawn_x_coords)
            spawn_max_x = max(spawn_x_coords)
            spawn_min_y = min(spawn_y_coords)
            spawn_max_y = max(spawn_y_coords)
            
            # 确保边界包含所有spawn points
            min_x = min(min_x, spawn_min_x)
            max_x = max(max_x, spawn_max_x)
            min_y = min(min_y, spawn_min_y)
            max_y = max(max_y, spawn_max_y)
            
            logger.info(f'Spawn points range: X=[{spawn_min_x:.1f}, {spawn_max_x:.1f}], Y=[{spawn_min_y:.1f}, {spawn_max_y:.1f}]')
        
        ax.set_xlim(min_x - margin, max_x + margin)
        ax.set_ylim(min_y - margin, max_y + margin)
        
        logger.info(f'View range: X=[{min_x - margin:.1f}, {max_x + margin:.1f}], Y=[{min_y - margin:.1f}, {max_y + margin:.1f}]')
    
    # 设置标题和标签
    ax.set_title('CARLA Road Network with Spawn Points', fontsize=16, fontweight='bold')
    ax.set_xlabel('X (meters)', fontsize=12)
    ax.set_ylabel('Y (meters)', fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', fontsize=10)
    ax.set_aspect('equal', adjustable='box')
    
    # 保存图像
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logger.info(f'Road network map saved to: {output_path}')
    
    plt.close()


if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Draw CARLA road network with spawn points')
    parser.add_argument('--output', type=str, required=True, help='Output file path for the image')
    args = parser.parse_args()
    
    # 基础组件初始化
    config = Config.from_yaml('config.yaml')                # 读取配置文件
    logger = Logging.from_config(config).get_logger('Main') # 设置日志记录器

    with CarlaContext.from_config(config) as context:        # 创建 CARLA 上下文
        draw_roadnet_with_spawn_points(context, args.output)
    
    logger.info('Goodbye!')