#!/usr/bin/env python3
"""
⚠️ AI GENERATED CODE, NOT VALIDATED YET
⚠️ AI 生成的代码, 未经验证

绘制 KITTI/Semantic KITTI 标定文件中的相机和雷达位置
"""

import argparse
import os
import numpy as np
import matplotlib
if 'DISPLAY' not in os.environ or os.environ.get('DISPLAY') == '':
    matplotlib.use('Agg')
else:
    try:
        matplotlib.use('Qt5Agg')
    except ImportError:
        try:
            matplotlib.use('TkAgg')
        except ImportError:
            matplotlib.use('Agg')
import matplotlib.pyplot as plt


def parse_calib_file(calib_path: str):
    """解析 KITTI 格式的标定文件"""
    calib_data = {}
    
    with open(calib_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(':', 1)
            if len(parts) != 2:
                continue
            
            key = parts[0].strip()
            values = [float(x) for x in parts[1].strip().split()]
            
            if len(values) == 12:
                calib_data[key] = np.array(values).reshape(3, 4)
    
    return calib_data


def extract_camera_position(P: np.ndarray, K: np.ndarray = None):
    """从投影矩阵P中提取相机位置"""
    if K is None:
        K = P[:, :3]
        R = np.eye(3)
        t = np.zeros(3)
        position = np.zeros(3)
    else:
        try:
            K_inv = np.linalg.inv(K)
            Rt = K_inv @ P
            R = Rt[:, :3]
            t = Rt[:, 3]
            
            U, _, Vt = np.linalg.svd(R)
            R = U @ Vt
            if np.linalg.det(R) < 0:
                R = U @ np.diag([1, 1, -1]) @ Vt
            
            position = -R.T @ t
        except:
            R = np.eye(3)
            position = np.zeros(3)
    
    return position, R, K


def extract_lidar_position(Tr: np.ndarray):
    """从Tr矩阵中提取雷达位置"""
    R = Tr[:, :3]
    t = Tr[:, 3]
    position = t
    return position, R


def draw_coordinate_frame(ax, origin, R, scale=1.0, label='', is_3d=True):
    """绘制坐标系框架"""
    axes_local = np.array([
        [scale, 0, 0],
        [0, scale, 0],
        [0, 0, scale]
    ])
    
    axes_world = (R @ axes_local.T).T
    
    colors = ['r', 'g', 'b']
    axis_labels = ['X', 'Y', 'Z']
    
    for i, (axis, color, axis_label) in enumerate(zip(axes_world, colors, axis_labels)):
        end = origin + axis
        if is_3d:
            ax.plot([origin[0], end[0]], 
                    [origin[1], end[1]], 
                    [origin[2], end[2]], 
                    color=color, linewidth=2, label=f'{label} {axis_label}' if i == 0 else '')
        else:
            ax.quiver(origin[0], origin[1], origin[2],
                     axis[0], axis[1], axis[2],
                     color=color, arrow_length_ratio=0.2, linewidth=2, alpha=0.8)
    
    if is_3d:
        ax.scatter(*origin, color='k', s=50)


def main():
    parser = argparse.ArgumentParser(
        description='绘制 KITTI/Semantic KITTI 标定文件中的相机和雷达位置'
    )
    parser.add_argument(
        'dataset_path',
        type=str,
        help='数据集基础路径（包含calib.txt的目录）'
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        default=None,
        help='输出图片路径（如果指定，将保存图片而不是显示窗口）'
    )
    
    args = parser.parse_args()
    
    calib_path = os.path.join(args.dataset_path, 'calib.txt')
    
    if not os.path.exists(calib_path):
        print(f"Error: calib.txt not found at {calib_path}")
        return
    
    calib_data = parse_calib_file(calib_path)
    
    if 'P0' not in calib_data:
        print("Error: P0 not found in calib.txt")
        return
    
    if 'Tr' not in calib_data:
        print("Error: Tr not found in calib.txt")
        return
    
    P0 = calib_data['P0']
    cam_position, cam_R, cam_K = extract_camera_position(P0)
    cam_R_kitti = np.eye(3)
    
    Tr = calib_data['Tr']
    lidar_position, lidar_R = extract_lidar_position(Tr)
    lidar_R_kitti = lidar_R
    
    other_cameras = []
    camera_idx = 1
    while f'P{camera_idx}' in calib_data:
        P_cam = calib_data[f'P{camera_idx}']
        try:
            cam_pos, cam_R_rel, _ = extract_camera_position(P_cam, K=cam_K)
            cam_R_cam = cam_R_rel @ cam_R_kitti
            other_cameras.append((cam_pos, cam_R_cam, f'Camera{camera_idx}'))
        except Exception as e:
            print(f"Warning: Failed to extract camera {camera_idx}: {e}")
        camera_idx += 1
    
    all_positions = [cam_position, lidar_position] + [pos for pos, _, _ in other_cameras]
    all_positions = np.array(all_positions)
    
    pos_min = all_positions.min(axis=0)
    pos_max = all_positions.max(axis=0)
    pos_range = pos_max - pos_min
    max_range = pos_range.max()
    
    if max_range < 1e-6:
        max_range = 2.0
        center = np.zeros(3)
    else:
        center = (pos_min + pos_max) / 2
        max_range = max_range * 1.2
    
    x_lim = [center[0] - max_range/2, center[0] + max_range/2]
    y_lim = [center[1] - max_range/2, center[1] + max_range/2]
    z_lim = [center[2] - max_range/2, center[2] + max_range/2]
    
    fig = plt.figure(figsize=(16, 12))
    coord_scale = max_range / 10
    
    def draw_sensor_2d(ax_subplot, pos, R, label, color, x_idx, y_idx):
        """在2D子图中绘制传感器位置和坐标系投影"""
        ax_subplot.scatter(pos[x_idx], pos[y_idx], color=color, s=100, marker='o', label=label, zorder=5)
        
        x_axis = R[:, 0] * coord_scale
        y_axis = R[:, 1] * coord_scale
        z_axis = R[:, 2] * coord_scale
        
        ax_subplot.arrow(pos[x_idx], pos[y_idx], x_axis[x_idx], x_axis[y_idx],
                        head_width=max_range/30, head_length=max_range/40, fc='r', ec='r', alpha=0.7)
        ax_subplot.arrow(pos[x_idx], pos[y_idx], y_axis[x_idx], y_axis[y_idx],
                        head_width=max_range/30, head_length=max_range/40, fc='g', ec='g', alpha=0.7)
        ax_subplot.arrow(pos[x_idx], pos[y_idx], z_axis[x_idx], z_axis[y_idx],
                        head_width=max_range/30, head_length=max_range/40, fc='b', ec='b', alpha=0.7)
    
    ax_xy = fig.add_subplot(2, 2, 1)
    draw_sensor_2d(ax_xy, cam_position, cam_R_kitti, 'Camera0', 'blue', 0, 1)
    draw_sensor_2d(ax_xy, lidar_position, lidar_R_kitti, 'Lidar', 'red', 0, 1)
    for cam_pos, cam_R_cam, cam_label in other_cameras:
        draw_sensor_2d(ax_xy, cam_pos, cam_R_cam, cam_label, 'green', 0, 1)
    ax_xy.set_xlabel('X (m, Right)', fontsize=10)
    ax_xy.set_ylabel('Y (m, Down)', fontsize=10)
    ax_xy.set_title('X-Y Plane (Top View)', fontsize=12)
    ax_xy.set_xlim(x_lim)
    ax_xy.set_ylim(y_lim)
    ax_xy.grid(True, alpha=0.3)
    ax_xy.legend(loc='upper right', fontsize=8)
    
    ax_xz = fig.add_subplot(2, 2, 2)
    draw_sensor_2d(ax_xz, cam_position, cam_R_kitti, 'Camera0', 'blue', 0, 2)
    draw_sensor_2d(ax_xz, lidar_position, lidar_R_kitti, 'Lidar', 'red', 0, 2)
    for cam_pos, cam_R_cam, cam_label in other_cameras:
        draw_sensor_2d(ax_xz, cam_pos, cam_R_cam, cam_label, 'green', 0, 2)
    ax_xz.set_xlabel('X (m, Right)', fontsize=10)
    ax_xz.set_ylabel('Z (m, Forward)', fontsize=10)
    ax_xz.set_title('X-Z Plane (Side View)', fontsize=12)
    ax_xz.set_xlim(x_lim)
    ax_xz.set_ylim(z_lim)
    ax_xz.grid(True, alpha=0.3)
    ax_xz.legend(loc='upper right', fontsize=8)
    
    ax_yz = fig.add_subplot(2, 2, 3)
    draw_sensor_2d(ax_yz, cam_position, cam_R_kitti, 'Camera0', 'blue', 1, 2)
    draw_sensor_2d(ax_yz, lidar_position, lidar_R_kitti, 'Lidar', 'red', 1, 2)
    for cam_pos, cam_R_cam, cam_label in other_cameras:
        draw_sensor_2d(ax_yz, cam_pos, cam_R_cam, cam_label, 'green', 1, 2)
    ax_yz.set_xlabel('Y (m, Down)', fontsize=10)
    ax_yz.set_ylabel('Z (m, Forward)', fontsize=10)
    ax_yz.set_title('Y-Z Plane (Front View)', fontsize=12)
    ax_yz.set_xlim(y_lim)
    ax_yz.set_ylim(z_lim)
    ax_yz.grid(True, alpha=0.3)
    ax_yz.legend(loc='upper right', fontsize=8)
    
    ax_3d = fig.add_subplot(2, 2, 4, projection='3d')
    draw_coordinate_frame(ax_3d, cam_position, cam_R_kitti, scale=coord_scale, label='Camera0', is_3d=True)
    draw_coordinate_frame(ax_3d, lidar_position, lidar_R_kitti, scale=coord_scale, label='Lidar', is_3d=True)
    for cam_pos, cam_R_cam, cam_label in other_cameras:
        draw_coordinate_frame(ax_3d, cam_pos, cam_R_cam, scale=coord_scale, label=cam_label, is_3d=True)
    
    ax_3d.set_xlabel('X (m, Right)', fontsize=10)
    ax_3d.set_ylabel('Y (m, Down)', fontsize=10)
    ax_3d.set_zlabel('Z (m, Forward)', fontsize=10)
    ax_3d.set_title('3D View (Camera Coordinate System)', fontsize=12)
    ax_3d.set_xlim(x_lim)
    ax_3d.set_ylim(y_lim)
    ax_3d.set_zlim(z_lim)
    
    handles, labels = ax_3d.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax_3d.legend(by_label.values(), by_label.keys(), loc='upper left', fontsize=8)
    ax_3d.grid(True, alpha=0.3)
    
    plt.suptitle('KITTI Calibration: Camera and Lidar Positions', fontsize=14, y=0.995)
    plt.tight_layout(rect=[0, 0, 1, 0.99])
    
    if args.output:
        plt.savefig(args.output, dpi=150, bbox_inches='tight')
        print(f"Image saved to: {args.output}")
    else:
        plt.show()


if __name__ == '__main__':
    main()

