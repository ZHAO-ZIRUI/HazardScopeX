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
        
        print("i:",i," loc:",location, "rot:",rotation)

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

# Town10HD_Opt
# i: 0  loc: Location(x=-64.644844, y=24.471010, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.159198, roll=0.000000)
# i: 1  loc: Location(x=-67.254570, y=27.963758, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.159198, roll=0.000000)
# i: 2  loc: Location(x=-87.623032, y=12.967159, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 3  loc: Location(x=-84.932762, y=16.474657, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 4  loc: Location(x=-103.179001, y=-14.434907, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-89.357758, roll=0.000000)
# i: 5  loc: Location(x=-106.649590, y=-17.073978, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-89.357758, roll=0.000000)
# i: 6  loc: Location(x=-110.963745, y=59.689358, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.642235, roll=0.000000)
# i: 7  loc: Location(x=-114.432091, y=56.850296, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.642235, roll=0.000000)
# i: 8  loc: Location(x=-111.120361, y=72.898865, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.642235, roll=0.000000)
# i: 9  loc: Location(x=-114.588699, y=70.059807, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.642235, roll=0.000000)
# i: 10  loc: Location(x=-24.336779, y=-57.785625, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.596735, roll=0.000000)
# i: 11  loc: Location(x=-110.197800, y=-9.842224, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.642235, roll=0.000000)
# i: 12  loc: Location(x=-113.648178, y=-14.281184, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.642235, roll=0.000000)
# i: 13  loc: Location(x=-109.929558, y=-23.428406, z=0.599995) rot: Rotation(pitch=0.000000, yaw=90.642235, roll=0.000000)
# i: 14  loc: Location(x=-113.403503, y=-25.767477, z=0.599995) rot: Rotation(pitch=0.000000, yaw=90.642235, roll=0.000000)
# i: 15  loc: Location(x=-56.866161, y=140.535553, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.352127, roll=0.000000)
# i: 16  loc: Location(x=-54.344658, y=137.050995, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.352127, roll=0.000000)
# i: 17  loc: Location(x=3.047784, y=130.210068, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.647827, roll=0.000000)
# i: 18  loc: Location(x=5.626226, y=133.726013, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.647827, roll=0.000000)
# i: 19  loc: Location(x=45.765675, y=137.459961, z=0.600001) rot: Rotation(pitch=0.000000, yaw=0.320448, roll=0.000000)
# i: 20  loc: Location(x=48.546078, y=140.975540, z=0.600001) rot: Rotation(pitch=0.000000, yaw=0.320448, roll=0.000000)
# i: 21  loc: Location(x=99.384415, y=-6.305729, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.390709, roll=0.000000)
# i: 22  loc: Location(x=53.122719, y=133.946625, z=0.600029) rot: Rotation(pitch=0.000000, yaw=-179.679535, roll=0.000000)
# i: 23  loc: Location(x=55.542278, y=130.460068, z=0.600029) rot: Rotation(pitch=0.000000, yaw=-179.679535, roll=0.000000)
# i: 24  loc: Location(x=-52.073921, y=100.189049, z=0.600000) rot: Rotation(pitch=0.000000, yaw=89.838760, roll=0.000000)
# i: 25  loc: Location(x=-48.567417, y=102.479195, z=0.600000) rot: Rotation(pitch=0.000000, yaw=89.838760, roll=0.000000)
# i: 26  loc: Location(x=-52.073921, y=63.538094, z=0.600000) rot: Rotation(pitch=0.000000, yaw=89.838760, roll=0.000000)
# i: 27  loc: Location(x=-48.582111, y=60.628242, z=0.600000) rot: Rotation(pitch=0.000000, yaw=89.838760, roll=0.000000)
# i: 28  loc: Location(x=-41.668587, y=89.745483, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-90.161217, roll=0.000000)
# i: 29  loc: Location(x=-45.160957, y=92.455330, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-90.161217, roll=0.000000)
# i: 30  loc: Location(x=-15.148191, y=69.714005, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.073273, roll=0.000000)
# i: 31  loc: Location(x=-1.013160, y=69.714005, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.073273, roll=0.000000)
# i: 32  loc: Location(x=98.800659, y=82.890846, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.390709, roll=0.000000)
# i: 33  loc: Location(x=14.130092, y=69.714005, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.073273, roll=0.000000)
# i: 34  loc: Location(x=6.006511, y=66.283257, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.926727, roll=0.000000)
# i: 35  loc: Location(x=-7.966957, y=66.283257, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.926727, roll=0.000000)
# i: 36  loc: Location(x=67.659744, y=69.822777, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.073273, roll=0.000000)
# i: 37  loc: Location(x=79.055290, y=69.822777, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.073273, roll=0.000000)
# i: 38  loc: Location(x=73.632927, y=66.358490, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.926727, roll=0.000000)
# i: 39  loc: Location(x=61.602592, y=66.358490, z=0.599999) rot: Rotation(pitch=0.000000, yaw=-179.926727, roll=0.000000)
# i: 40  loc: Location(x=106.028816, y=67.419983, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-89.609253, roll=0.000000)
# i: 41  loc: Location(x=109.502762, y=71.243790, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-89.609253, roll=0.000000)
# i: 42  loc: Location(x=106.002838, y=92.812851, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-89.609253, roll=0.000000)
# i: 43  loc: Location(x=40.389641, y=41.945496, z=0.600000) rot: Rotation(pitch=0.000000, yaw=89.248878, roll=0.000000)
# i: 44  loc: Location(x=109.523270, y=89.836723, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-89.609253, roll=0.000000)
# i: 45  loc: Location(x=65.235275, y=13.414804, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 46  loc: Location(x=62.025547, y=16.905891, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 47  loc: Location(x=45.382851, y=13.414804, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 48  loc: Location(x=43.373123, y=16.909227, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 49  loc: Location(x=15.143111, y=16.681334, z=0.700000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 50  loc: Location(x=20.452812, y=13.196091, z=0.700000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 51  loc: Location(x=-20.115120, y=16.749100, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 52  loc: Location(x=-17.105402, y=13.257457, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 53  loc: Location(x=-0.764156, y=24.613132, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.159198, roll=0.000000)
# i: 54  loc: Location(x=19.350212, y=137.459961, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.320448, roll=0.000000)
# i: 55  loc: Location(x=-3.973868, y=28.104216, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.159198, roll=0.000000)
# i: 56  loc: Location(x=19.600943, y=24.611189, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.159198, roll=0.000000)
# i: 57  loc: Location(x=17.091217, y=28.104216, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.159198, roll=0.000000)
# i: 58  loc: Location(x=77.008102, y=24.849667, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.159198, roll=0.000000)
# i: 59  loc: Location(x=74.798752, y=28.343533, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.159198, roll=0.000000)
# i: 60  loc: Location(x=10.912545, y=-57.401386, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-0.023438, roll=0.000000)
# i: 61  loc: Location(x=7.411115, y=-60.899998, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-0.023438, roll=0.000000)
# i: 62  loc: Location(x=106.513153, y=-21.554596, z=0.900000) rot: Rotation(pitch=0.000000, yaw=-91.519577, roll=0.000000)
# i: 63  loc: Location(x=109.956909, y=-27.333675, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-94.682335, roll=0.000000)
# i: 64  loc: Location(x=30.018200, y=133.947205, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.679535, roll=0.000000)
# i: 65  loc: Location(x=109.946968, y=-17.187952, z=0.599999) rot: Rotation(pitch=0.000000, yaw=-89.609253, roll=0.000000)
# i: 66  loc: Location(x=-6.554498, y=137.225952, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.352119, roll=0.000000)
# i: 67  loc: Location(x=-41.853989, y=-30.438610, z=0.600071) rot: Rotation(pitch=0.000000, yaw=-89.567680, roll=0.000000)
# i: 68  loc: Location(x=-52.073921, y=82.654968, z=0.600000) rot: Rotation(pitch=0.000000, yaw=89.838760, roll=0.000000)
# i: 69  loc: Location(x=-28.581730, y=140.535553, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.352127, roll=0.000000)
# i: 70  loc: Location(x=-18.385923, y=130.210068, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.647827, roll=0.000000)
# i: 71  loc: Location(x=-9.875875, y=-57.551670, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.596741, roll=0.000000)
# i: 72  loc: Location(x=11.176284, y=-64.398766, z=0.600000) rot: Rotation(pitch=0.000000, yaw=179.976562, roll=0.000000)
# i: 73  loc: Location(x=-15.407496, y=133.728470, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.647827, roll=0.000000)
# i: 74  loc: Location(x=14.274853, y=-67.899994, z=0.600000) rot: Rotation(pitch=0.000000, yaw=179.976562, roll=0.000000)
# i: 75  loc: Location(x=-110.764435, y=46.660076, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.642235, roll=0.000000)
# i: 76  loc: Location(x=99.078560, y=42.141800, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.390709, roll=0.000000)
# i: 77  loc: Location(x=-78.034149, y=12.967159, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 78  loc: Location(x=-71.269684, y=132.314896, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-167.127060, roll=0.000000)
# i: 79  loc: Location(x=-41.668877, y=48.905540, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-90.161217, roll=0.000000)
# i: 80  loc: Location(x=-87.276062, y=24.441530, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.159198, roll=0.000000)
# i: 81  loc: Location(x=-5.783490, y=-64.548683, z=0.600005) rot: Rotation(pitch=0.000000, yaw=-179.403244, roll=0.000000)
# i: 82  loc: Location(x=-27.800329, y=-61.284046, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.596735, roll=0.000000)
# i: 83  loc: Location(x=-27.160252, y=137.044220, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.352127, roll=0.000000)
# i: 84  loc: Location(x=52.789970, y=69.822777, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.073273, roll=0.000000)
# i: 85  loc: Location(x=-89.885788, y=27.934278, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.159198, roll=0.000000)
# i: 86  loc: Location(x=-66.794197, y=12.998389, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 87  loc: Location(x=106.019249, y=50.869312, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-89.609253, roll=0.000000)
# i: 88  loc: Location(x=21.630592, y=140.972717, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.320448, roll=0.000000)
# i: 89  loc: Location(x=-52.330811, y=-14.039614, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.432327, roll=0.000000)
# i: 90  loc: Location(x=-64.103928, y=16.505888, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 91  loc: Location(x=-76.666107, y=24.471010, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.159198, roll=0.000000)
# i: 92  loc: Location(x=99.434853, y=-19.657715, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.844849, roll=0.000000)
# i: 93  loc: Location(x=-25.516296, y=24.613134, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.159198, roll=0.000000)
# i: 94  loc: Location(x=-79.275833, y=27.963758, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.159198, roll=0.000000)
# i: 95  loc: Location(x=-45.340046, y=-25.565022, z=0.600071) rot: Rotation(pitch=0.000000, yaw=-89.567680, roll=0.000000)
# i: 96  loc: Location(x=-75.343872, y=16.474657, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 97  loc: Location(x=44.028950, y=52.548698, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-90.751091, roll=0.000000)
# i: 98  loc: Location(x=109.502762, y=53.293152, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-89.609253, roll=0.000000)
# i: 99  loc: Location(x=-52.310936, y=-1.585238, z=0.600000) rot: Rotation(pitch=0.000000, yaw=89.838760, roll=0.000000)
# i: 100  loc: Location(x=-106.686729, y=-4.847458, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-89.357758, roll=0.000000)
# i: 101  loc: Location(x=-28.726021, y=28.104218, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.159198, roll=0.000000)
# i: 102  loc: Location(x=-48.819988, y=-4.795075, z=0.600000) rot: Rotation(pitch=0.000000, yaw=89.838760, roll=0.000000)
# i: 103  loc: Location(x=-45.311253, y=-1.694395, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-90.161217, roll=0.000000)
# i: 104  loc: Location(x=-41.825108, y=-6.604221, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-90.161217, roll=0.000000)
# i: 105  loc: Location(x=83.075226, y=13.414804, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 106  loc: Location(x=-68.735168, y=129.303848, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-167.127060, roll=0.000000)
# i: 107  loc: Location(x=59.812996, y=24.850224, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.159198, roll=0.000000)
# i: 108  loc: Location(x=-52.186737, y=42.565125, z=0.600000) rot: Rotation(pitch=0.000000, yaw=89.838760, roll=0.000000)
# i: 109  loc: Location(x=-67.045288, y=-68.693169, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.403244, roll=0.000000)
# i: 110  loc: Location(x=-48.839951, y=-17.213200, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.432327, roll=0.000000)
# i: 111  loc: Location(x=-45.317440, y=-11.645325, z=0.600002) rot: Rotation(pitch=0.000000, yaw=-90.161217, roll=0.000000)
# i: 112  loc: Location(x=102.566177, y=43.965668, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.390709, roll=0.000000)
# i: 113  loc: Location(x=-9.175960, y=140.709900, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.352119, roll=0.000000)
# i: 114  loc: Location(x=29.235720, y=16.765228, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 115  loc: Location(x=-41.833862, y=-16.555164, z=0.600002) rot: Rotation(pitch=0.000000, yaw=-90.161217, roll=0.000000)
# i: 116  loc: Location(x=-48.674351, y=46.955273, z=0.600000) rot: Rotation(pitch=0.000000, yaw=89.838760, roll=0.000000)
# i: 117  loc: Location(x=80.265495, y=16.907003, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 118  loc: Location(x=27.142294, y=66.283257, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.926727, roll=0.000000)
# i: 119  loc: Location(x=57.403645, y=28.343533, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.159198, roll=0.000000)
# i: 120  loc: Location(x=-103.216141, y=-2.208392, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-89.357758, roll=0.000000)
# i: 121  loc: Location(x=-64.581863, y=-65.167366, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.403244, roll=0.000000)
# i: 122  loc: Location(x=-48.565468, y=85.645119, z=0.600000) rot: Rotation(pitch=0.000000, yaw=89.838760, roll=0.000000)
# i: 123  loc: Location(x=-13.339423, y=-61.050091, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.596741, roll=0.000000)
# i: 124  loc: Location(x=-27.022133, y=69.714005, z=0.600000) rot: Rotation(pitch=0.000000, yaw=0.073273, roll=0.000000)
# i: 125  loc: Location(x=-114.232773, y=43.821014, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.642235, roll=0.000000)
# i: 126  loc: Location(x=-52.133560, y=-40.180298, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.432304, roll=0.000000)
# i: 127  loc: Location(x=102.980186, y=-22.705795, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.844849, roll=0.000000)
# i: 128  loc: Location(x=32.337723, y=130.460068, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.679535, roll=0.000000)
# i: 129  loc: Location(x=-41.491478, y=111.945290, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-90.161217, roll=0.000000)
# i: 130  loc: Location(x=-44.982998, y=114.955147, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-90.161217, roll=0.000000)
# i: 131  loc: Location(x=109.913483, y=-6.925447, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-89.609253, roll=0.000000)
# i: 132  loc: Location(x=106.377342, y=-1.649443, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-89.609253, roll=0.000000)
# i: 133  loc: Location(x=102.317673, y=80.414726, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.390709, roll=0.000000)
# i: 134  loc: Location(x=32.045444, y=13.273029, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.840790, roll=0.000000)
# i: 135  loc: Location(x=-48.642700, y=-43.353889, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.432304, roll=0.000000)
# i: 136  loc: Location(x=85.982246, y=66.358490, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-179.926727, roll=0.000000)
# i: 137  loc: Location(x=-45.149696, y=55.715389, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-90.161217, roll=0.000000)
# i: 138  loc: Location(x=-52.330811, y=-28.861330, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.432327, roll=0.000000)
# i: 139  loc: Location(x=-48.839951, y=-32.034920, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.432327, roll=0.000000)
# i: 140  loc: Location(x=-41.749878, y=-41.373684, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-89.567680, roll=0.000000)
# i: 141  loc: Location(x=-45.235935, y=-36.500095, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-89.567680, roll=0.000000)
# i: 142  loc: Location(x=102.930038, y=-9.381519, z=0.600000) rot: Rotation(pitch=0.000000, yaw=90.390709, roll=0.000000)
# i: 143  loc: Location(x=26.382587, y=-57.401386, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-0.023438, roll=0.000000)
# i: 144  loc: Location(x=22.881157, y=-60.899998, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-0.023438, roll=0.000000)
# i: 145  loc: Location(x=-15.448323, y=-68.007065, z=0.600005) rot: Rotation(pitch=0.000000, yaw=-179.403244, roll=0.000000)
# i: 146  loc: Location(x=-18.782679, y=-64.708092, z=0.900005) rot: Rotation(pitch=0.000000, yaw=-179.403244, roll=0.000000)
# i: 147  loc: Location(x=29.894043, y=-64.398766, z=0.600000) rot: Rotation(pitch=0.000000, yaw=179.976562, roll=0.000000)
# i: 148  loc: Location(x=32.992611, y=-67.899994, z=0.600000) rot: Rotation(pitch=0.000000, yaw=179.976562, roll=0.000000)
# i: 149  loc: Location(x=47.557049, y=-57.225220, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-0.023438, roll=0.000000)
# i: 150  loc: Location(x=44.055626, y=-60.723831, z=0.600000) rot: Rotation(pitch=0.000000, yaw=-0.023438, roll=0.000000)
# i: 151  loc: Location(x=54.469772, y=-64.348633, z=0.600000) rot: Rotation(pitch=0.000000, yaw=179.976562, roll=0.000000)
# i: 152  loc: Location(x=57.568340, y=-67.849854, z=0.600000) rot: Rotation(pitch=0.000000, yaw=179.976562, roll=0.000000)
# i: 153  loc: Location(x=-2.647038, y=-68.049721, z=0.600005) rot: Rotation(pitch=0.000000, yaw=-179.403244, roll=0.000000)
# i: 154  loc: Location(x=106.416290, y=-12.711931, z=0.599999) rot: Rotation(pitch=0.000000, yaw=-89.609253, roll=0.000000)