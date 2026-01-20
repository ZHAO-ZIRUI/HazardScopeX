import carla
import random

def draw_waypoints_with_road_colors(map_name='Town01'):
    """在不同地图上绘制waypoint"""
    
    # 连接CARLA服务器
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)
    
    # 加载指定地图
    world = client.load_world(map_name)
    
    # 获取地图
    map = world.get_map()
    
    # 获取所有waypoint
    waypoints = map.generate_waypoints(distance=1.0)
    
    # 为不同道路创建颜色
    # road_colors = {}
    road_list = []
    
    # # 使用固定种子以获得可重复的颜色
    # random.seed(42)
    
    # for waypoint in waypoints:
    #     road_id = waypoint.road_id
    #     road_list.append(road_id)
        
    #     if road_id not in road_colors:
    #         # 使用HSL颜色空间获得更均匀分布的颜色
    #         hue = (road_id * 137) % 360  # 使用黄金角度近似
    #         r, g, b = hsv_to_rgb(hue/360.0, 0.8, 0.9)
    #         road_colors[road_id] = carla.Color(int(r*255), int(g*255), int(b*255))

    # road_list = list(set(road_list))
    


    for waypoint in waypoints:
        road_id = waypoint.road_id
        if road_id not in road_list:
            road_list.append(road_id)

    

    
    # 绘制waypoint
    for i, waypoint in enumerate(waypoints):
        # color = road_colors[waypoint.road_id]
        r = random
        g = 
        b =
        print("waypoint.road_id:",waypoint.road_id," ",carla.Color(int(255.0 * road_list.index(waypoint.road_id) / len(road_list)), 0, 255 - int(255.0 * road_list.index(waypoint.road_id) / len(road_list))))
        
        # 绘制点
        world.debug.draw_point(
            waypoint.transform.location + carla.Location(z=0.2),
            size=0.08,
            color=carla.Color(int(255.0 * road_list.index(waypoint.road_id) / len(road_list)), 0, 255 - int(255.0 * road_list.index(waypoint.road_id) / len(road_list))),
            life_time=1000.0
        )
        
        # 每1000个点输出一次进度
        if i % 1000 == 0:
            print(f"已绘制 {i}/{len(waypoints)} 个点")

    print(f"地图 '{map_name}' 上绘制了 {len(waypoints)} 个waypoints")
    print(f"道路数量: {len(road_list)}")
    
    # return road_colors
    return 

def hsv_to_rgb(h, s, v):
    """HSV到RGB的转换"""
    if s == 0.0:
        return v, v, v
    i = int(h*6.0)
    f = (h*6.0) - i
    p = v*(1.0 - s)
    q = v*(1.0 - s*f)
    t = v*(1.0 - s*(1.0-f))
    i = i%6
    if i == 0:
        return v, t, p
    if i == 1:
        return q, v, p
    if i == 2:
        return p, v, t
    if i == 3:
        return p, q, v
    if i == 4:
        return t, p, v
    if i == 5:
        return v, p, q

if __name__ == "__main__":
    # 可以尝试不同的地图
    maps = ['Town10HD_Opt']
    
    for map_name in maps[:1]:  # 只绘制第一个地图
        try:
            draw_waypoints_with_road_colors(map_name)
            break
        except Exception as e:
            print(f"无法加载地图 {map_name}: {e}")