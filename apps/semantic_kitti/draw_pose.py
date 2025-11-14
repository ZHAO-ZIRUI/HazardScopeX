#!/usr/bin/env python3
"""
⚠️ AI GENERATED CODE, NOT VALIDATED YET
⚠️ AI 生成的代码, 未经验证

绘制 KITTI/Semantic KITTI 位姿文件中的路径
"""

import argparse
import os
import numpy as np
import matplotlib
# Ubuntu上的GUI后端设置
if 'DISPLAY' not in os.environ or os.environ.get('DISPLAY') == '':
    matplotlib.use('Agg')  # 非交互式后端，用于保存图片
else:
    # Ubuntu上优先使用Qt5Agg，如果不可用则尝试TkAgg
    try:
        matplotlib.use('Qt5Agg')
    except ImportError:
        try:
            matplotlib.use('TkAgg')
        except ImportError:
            matplotlib.use('Agg')
import matplotlib.pyplot as plt


def parse_pose_file(pose_path: str):
    """解析 KITTI 格式的位姿文件
    
    每行包含12个浮点数，表示3x4变换矩阵（按行展开）
    
    Args:
        pose_path: 位姿文件路径
        
    Returns:
        list: 位姿矩阵列表，每个元素是3x4的numpy数组
    """
    poses = []
    
    with open(pose_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # 解析12个浮点数
            values = [float(x) for x in line.split()]
            if len(values) == 12:
                pose_matrix = np.array(values).reshape(3, 4)
                poses.append(pose_matrix)
    
    return poses


def pose_matrix_to_position(pose_matrix: np.ndarray):
    """从3x4位姿矩阵中提取位置
    
    Args:
        pose_matrix: 3x4变换矩阵
        
    Returns:
        np.ndarray: 位置向量 (3,)
    """
    return pose_matrix[:, 3]


def pose_matrix_to_rotation(pose_matrix: np.ndarray):
    """从3x4位姿矩阵中提取旋转矩阵
    
    Args:
        pose_matrix: 3x4变换矩阵
        
    Returns:
        np.ndarray: 旋转矩阵 (3,3)
    """
    return pose_matrix[:, :3]


def main():
    parser = argparse.ArgumentParser(
        description='绘制 KITTI/Semantic KITTI 位姿文件中的路径'
    )
    parser.add_argument(
        'dataset_path',
        type=str,
        help='数据集基础路径（包含pose.txt的目录）'
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        default=None,
        help='输出图片路径（如果指定，将保存图片而不是显示窗口）'
    )
    
    args = parser.parse_args()
    
    # 构建pose.txt路径
    pose_path = os.path.join(args.dataset_path, 'pose.txt')
    
    if not os.path.exists(pose_path):
        print(f"Error: pose.txt not found at {pose_path}")
        return
    
    # 解析位姿文件
    poses = parse_pose_file(pose_path)
    
    if len(poses) == 0:
        print("Error: No poses found in pose.txt")
        return
    
    print(f"Found {len(poses)} poses")
    
    # 提取所有位置
    positions = np.array([pose_matrix_to_position(pose) for pose in poses])
    
    # 计算统一的坐标轴范围
    pos_min = positions.min(axis=0)
    pos_max = positions.max(axis=0)
    pos_range = pos_max - pos_min
    max_range = pos_range.max()
    
    # 如果所有点都在同一位置，设置一个默认范围
    if max_range < 1e-6:
        max_range = 1.0
        center = np.zeros(3)
    else:
        center = (pos_min + pos_max) / 2
        max_range = max_range * 1.1  # 添加10%的边距
    
    # 统一的坐标轴范围
    x_lim = [center[0] - max_range/2, center[0] + max_range/2]
    y_lim = [center[1] - max_range/2, center[1] + max_range/2]
    z_lim = [center[2] - max_range/2, center[2] + max_range/2]
    
    # 创建包含4个子图的图形
    fig = plt.figure(figsize=(16, 12))
    
    # 子图1: X-Y平面（俯视图）
    ax_xy = fig.add_subplot(2, 2, 1)
    ax_xy.plot(positions[:, 0], positions[:, 1], 'b-', linewidth=2, label='Trajectory', alpha=0.7)
    ax_xy.scatter(positions[0, 0], positions[0, 1], color='g', s=100, marker='o', label='Start', zorder=5)
    ax_xy.scatter(positions[-1, 0], positions[-1, 1], color='r', s=100, marker='s', label='End', zorder=5)
    ax_xy.set_xlabel('X (m)', fontsize=10)
    ax_xy.set_ylabel('Y (m)', fontsize=10)
    ax_xy.set_title('X-Y Plane (Top View)', fontsize=12)
    ax_xy.set_xlim(x_lim)
    ax_xy.set_ylim(y_lim)
    ax_xy.grid(True, alpha=0.3)
    ax_xy.legend(loc='upper right', fontsize=8)
    
    # 子图2: X-Z平面（侧视图）
    ax_xz = fig.add_subplot(2, 2, 2)
    ax_xz.plot(positions[:, 0], positions[:, 2], 'b-', linewidth=2, label='Trajectory', alpha=0.7)
    ax_xz.scatter(positions[0, 0], positions[0, 2], color='g', s=100, marker='o', label='Start', zorder=5)
    ax_xz.scatter(positions[-1, 0], positions[-1, 2], color='r', s=100, marker='s', label='End', zorder=5)
    ax_xz.set_xlabel('X (m)', fontsize=10)
    ax_xz.set_ylabel('Z (m)', fontsize=10)
    ax_xz.set_title('X-Z Plane (Side View)', fontsize=12)
    ax_xz.set_xlim(x_lim)
    ax_xz.set_ylim(z_lim)
    ax_xz.grid(True, alpha=0.3)
    ax_xz.legend(loc='upper right', fontsize=8)
    
    # 子图3: Y-Z平面（前视图）
    ax_yz = fig.add_subplot(2, 2, 3)
    ax_yz.plot(positions[:, 1], positions[:, 2], 'b-', linewidth=2, label='Trajectory', alpha=0.7)
    ax_yz.scatter(positions[0, 1], positions[0, 2], color='g', s=100, marker='o', label='Start', zorder=5)
    ax_yz.scatter(positions[-1, 1], positions[-1, 2], color='r', s=100, marker='s', label='End', zorder=5)
    ax_yz.set_xlabel('Y (m)', fontsize=10)
    ax_yz.set_ylabel('Z (m)', fontsize=10)
    ax_yz.set_title('Y-Z Plane (Front View)', fontsize=12)
    ax_yz.set_xlim(y_lim)
    ax_yz.set_ylim(z_lim)
    ax_yz.grid(True, alpha=0.3)
    ax_yz.legend(loc='upper right', fontsize=8)
    
    # 子图4: 3D视图（按相机坐标系绘制）
    ax_3d = fig.add_subplot(2, 2, 4, projection='3d')
    ax_3d.plot(positions[:, 0], positions[:, 1], positions[:, 2], 
               'b-', linewidth=2, label='Trajectory', alpha=0.7)
    ax_3d.scatter(positions[0, 0], positions[0, 1], positions[0, 2], 
                 color='g', s=100, marker='o', label='Start', zorder=5)
    ax_3d.scatter(positions[-1, 0], positions[-1, 1], positions[-1, 2], 
                 color='r', s=100, marker='s', label='End', zorder=5)
    
    # 绘制相机坐标系框架（在关键帧位置）
    # KITTI相机坐标系：X右（红色），Y下（绿色），Z前（蓝色）
    coord_scale = max_range / 15  # 坐标轴长度
    
    # 绘制起点和终点的相机坐标系
    key_frames = [0, len(poses) - 1]
    for frame_idx in key_frames:
        pose = poses[frame_idx]
        pos = positions[frame_idx]
        R = pose_matrix_to_rotation(pose)
        
        # 绘制X轴（右，红色）
        x_axis = R[:, 0] * coord_scale
        ax_3d.quiver(pos[0], pos[1], pos[2],
                    x_axis[0], x_axis[1], x_axis[2],
                    color='r', arrow_length_ratio=0.2, linewidth=2, alpha=0.8)
        
        # 绘制Y轴（下，绿色）
        y_axis = R[:, 1] * coord_scale
        ax_3d.quiver(pos[0], pos[1], pos[2],
                    y_axis[0], y_axis[1], y_axis[2],
                    color='g', arrow_length_ratio=0.2, linewidth=2, alpha=0.8)
        
        # 绘制Z轴（前，蓝色）
        z_axis = R[:, 2] * coord_scale
        ax_3d.quiver(pos[0], pos[1], pos[2],
                    z_axis[0], z_axis[1], z_axis[2],
                    color='b', arrow_length_ratio=0.2, linewidth=2, alpha=0.8)
    
    # 每隔一定间隔绘制前进方向箭头（Z轴方向）
    arrow_interval = max(1, len(poses) // 20)  # 最多显示20个箭头
    for i in range(0, len(poses), arrow_interval):
        if i in key_frames:
            continue  # 跳过已经绘制完整坐标系的帧
        pose = poses[i]
        pos = positions[i]
        R = pose_matrix_to_rotation(pose)
        
        # 绘制Z轴方向（前进方向，在KITTI相机坐标系中）
        forward_direction = R[:, 2]  # Z轴（前）
        arrow_length = max_range / 25  # 箭头长度稍小，避免与坐标系重叠
        
        ax_3d.quiver(pos[0], pos[1], pos[2],
                    forward_direction[0] * arrow_length,
                    forward_direction[1] * arrow_length,
                    forward_direction[2] * arrow_length,
                    color='orange', arrow_length_ratio=0.3, alpha=0.5, linewidth=1)
    
    ax_3d.set_xlabel('X (m, Right)', fontsize=10)
    ax_3d.set_ylabel('Y (m, Down)', fontsize=10)
    ax_3d.set_zlabel('Z (m, Forward)', fontsize=10)
    ax_3d.set_title('3D View (Camera Coordinate System)', fontsize=12)
    ax_3d.set_xlim(x_lim)
    ax_3d.set_ylim(y_lim)
    ax_3d.set_zlim(z_lim)
    ax_3d.legend(loc='upper left', fontsize=8)
    ax_3d.grid(True, alpha=0.3)
    
    # 打印统计信息
    total_distance = np.sum(np.linalg.norm(np.diff(positions, axis=0), axis=1))
    straight_distance = np.linalg.norm(positions[-1] - positions[0])
    print(f"Total distance: {total_distance:.2f} m")
    print(f"Straight-line distance: {straight_distance:.2f} m")
    print(f"Path efficiency: {straight_distance/total_distance*100:.1f}%")
    
    plt.suptitle('KITTI Pose: Trajectory Visualization', fontsize=14, y=0.995)
    plt.tight_layout(rect=[0, 0, 1, 0.99])
    
    # 如果指定了输出路径，保存图片；否则显示窗口
    if args.output:
        plt.savefig(args.output, dpi=150, bbox_inches='tight')
        print(f"Image saved to: {args.output}")
    else:
        plt.show()


if __name__ == '__main__':
    main()

