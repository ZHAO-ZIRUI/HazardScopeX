import carla
import math

# def main():
#     try:
#         # 连接到Carla服务器
#         client = carla.Client('localhost', 2000)
#         client.set_timeout(10.0)
        
#         # 加载地图
#         map_name = 'Town10HD_Opt'
#         # map_name = 'SUSTech_COE_ParkingLot'
#         world = client.load_world(map_name)
#         print(f"成功连接到Carla模拟器并加载地图{map_name}")
        
#         # 获取所有生成点
#         spawn_points = world.get_map().get_spawn_points()
#         print(f"地图中共有 {len(spawn_points)} 个车辆生成点")
        
#         # 设置矩形框参数
#         vehicle_length = 4.5  # 车辆长度（米）
#         vehicle_width = 2.0   # 车辆宽度（米）
        
#         # 指定要绘制的生成点
#         blue_spawn_points = [93, 53, 56, 107, 58]
#         red_spawn_point = 101
        
#         # 绘制蓝色矩形框
#         for spawn_index in blue_spawn_points:
#             if spawn_index < len(spawn_points):
#                 draw_vehicle_bounding_box(world, spawn_points[spawn_index], 
#                                         vehicle_length, vehicle_width, 
#                                         carla.Color(0, 0, 255))  # 蓝色
#                 print(f"在生成点 {spawn_index} 绘制了蓝色矩形框")
#             else:
#                 print(f"警告: 生成点 {spawn_index} 不存在，地图中只有 {len(spawn_points)} 个生成点")
        
#         # 绘制红色矩形框
#         if red_spawn_point < len(spawn_points):
#             draw_vehicle_bounding_box(world, spawn_points[red_spawn_point], 
#                                     vehicle_length, vehicle_width, 
#                                     carla.Color(255, 0, 0))  # 红色
#             print(f"在生成点 {red_spawn_point} 绘制了红色矩形框")
#         else:
#             print(f"警告: 生成点 {red_spawn_point} 不存在，地图中只有 {len(spawn_points)} 个生成点")
        
#         print("所有矩形框绘制完成！矩形框将在模拟器中显示1000秒")
        
#     except Exception as e:
#         print(f"发生错误: {e}")


def main():
    try:
        # 连接到Carla服务器
        client = carla.Client('localhost', 2000)
        client.set_timeout(15.0)
        
        # 加载地图
        # world = client.load_world('SUSTech_COE_ParkingLot')
        # print("成功连接到Carla模拟器并加载地图SUSTech_COE_ParkingLot")
        world = client.load_world('Town10HD_Opt')
        print("成功连接到Carla模拟器并加载地图Town10HD_Opt")
        
        # 获取所有生成点
        spawn_points = world.get_map().get_spawn_points()
        print(f"地图中共有 {len(spawn_points)} 个车辆生成点")
        
        # 设置矩形框参数
        vehicle_length = 4.5  # 车辆长度（米）
        vehicle_width = 2.0   # 车辆宽度（米）
        
        # 在所有生成点绘制蓝色矩形框并标注编号
        for i, spawn_point in enumerate(spawn_points):
            # 绘制蓝色矩形框
            draw_vehicle_bounding_box(world, spawn_point, vehicle_length, vehicle_width, carla.Color(0, 0, 255), i)
            
            # 标注生成点编号
            label_location = spawn_point.location + carla.Location(z=2.0)  # 在生成点上方2米处标注
            world.debug.draw_string(
                label_location, 
                str(i), 
                draw_shadow=False, 
                color=carla.Color(255, 0, 255),  # 白色文字
                life_time=1000.0,
                persistent_lines=True
            )
            
            # print(f"已绘制生成点 {i} 的矩形框和编号")
        
        

        # WAYPOINTS = [
        #     carla.Location(x=-80,y=80,z=1),
        #     carla.Location(x=-40,y=40,z=1),
        #     carla.Location(x=-30,y=30,z=1),
        #     carla.Location(x=-20,y=20,z=1),
        #     carla.Location(x=-10,y=10,z=1),
        #     carla.Location(x=0,y=0,z=1),
        #     carla.Location(x=10,y=-10,z=1),
        #     carla.Location(x=20,y=-20,z=1),
        #     carla.Location(x=30,y=-30,z=1),
        #     carla.Location(x=40,y=-40,z=1),
        #     carla.Location(x=80,y=-80,z=1),
        # ]

        # for i in range(len(WAYPOINTS)):
        #     # print(i)
        #     if not i == 0:
        #         # print("draw line:",WAYPOINTS[i-1]," ",WAYPOINTS[i])
        #         world.debug.draw_line(WAYPOINTS[i-1],WAYPOINTS[i],thickness=5,color=carla.Color(255 - 10 * i,10 * i,10 * i),life_time=0)
        
        print(f"所有 {len(spawn_points)} 个生成点的矩形框和编号绘制完成！")

    except Exception as e:
        print(f"发生错误: {e}")

def draw_vehicle_bounding_box(world, spawn_point, length, width, color, i):
    """
    在指定生成点绘制车辆边界框
    
    参数:
    world: Carla世界对象
    spawn_point: 生成点变换信息
    length: 车辆长度
    width: 车辆宽度
    color: 框线颜色
    """
    try:
        # 获取生成点的位置和旋转
        location = spawn_point.location
        rotation = spawn_point.rotation
        
        # print("i:",i," loc:",location, "rot:",rotation)

        # 计算矩形的四个角点（相对于车辆中心）
        half_length = length / 2.0
        half_width = width / 2.0
        
        # 本地坐标系下的四个角点
        corners_local = [
            carla.Location(x=half_length, y=-half_width, z=0),  # 前右
            carla.Location(x=half_length, y=half_width, z=0),   # 前左
            carla.Location(x=-half_length, y=half_width, z=0),  # 后左
            carla.Location(x=-half_length, y=-half_width, z=0)  # 后右
        ]
        
        
        # 将角点转换到世界坐标系
        corners_world = []
        for corner in corners_local:
            # 应用旋转
            rotated_corner = rotate_point(corner, rotation.yaw)
            # 加上位置偏移
            world_corner = location + rotated_corner
            corners_world.append(world_corner)
        
        # 绘制矩形框的边
        for i in range(4):
            start_point = corners_world[i]
            end_point = corners_world[(i + 1) % 4]
            
            # 绘制线段
            world.debug.draw_line(
                start_point, end_point,
                thickness=0.1,
                color=color,
                life_time=1000.0  # 显示1000秒
            )
        
        # 绘制方向箭头（指示车辆前方）
        front_center_local = carla.Location(x=half_length, y=0, z=0)
        rotated_front = rotate_point(front_center_local, rotation.yaw)
        front_center_world = location + rotated_front
        
        world.debug.draw_arrow(
            location, front_center_world,
            thickness=0.05,
            arrow_size=0.2,
            color=color,
            life_time=1000.0
        )
        
    except Exception as e:
        print(f"绘制矩形框时出错: {e}")

def rotate_point(point, yaw_degrees):
    """
    将点绕Z轴旋转指定角度（偏航角）
    
    参数:
    point: 要旋转的点
    yaw_degrees: 偏航角（度）
    
    返回:
    旋转后的点
    """
    yaw_radians = math.radians(yaw_degrees)
    cos_yaw = math.cos(yaw_radians)
    sin_yaw = math.sin(yaw_radians)
    
    # 绕Z轴旋转矩阵
    x_rotated = point.x * cos_yaw - point.y * sin_yaw
    y_rotated = point.x * sin_yaw + point.y * cos_yaw
    
    return carla.Location(x=x_rotated, y=y_rotated, z=point.z)

if __name__ == '__main__':
    main()