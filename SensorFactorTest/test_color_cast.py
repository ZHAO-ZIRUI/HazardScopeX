import carla
import numpy as np
from PIL import Image
import os

os.makedirs("./images", exist_ok=True)

client = carla.Client("localhost", 2000)
world = client.get_world()
bp_lib = world.get_blueprint_library()

# 设置白天天气
weather = carla.WeatherParameters()
weather.sun_altitude_angle = 45  # 白天
world.set_weather(weather)

# 白平衡温度等级（色温值）
temp_levels = [4500, 3500, 2500]  # 6500K为中性
level_names = ["I级", "II级", "III级"]

for level, temp in enumerate(temp_levels):
    # 创建车辆
    vehicle_bp = bp_lib.find("vehicle.tesla.model3")
    vehicle = world.spawn_actor(vehicle_bp, world.get_map().get_spawn_points()[1])
    
    # 创建摄像头并设置白平衡温度
    camera_bp = bp_lib.find("sensor.camera.rgb")
    camera_bp.set_attribute("temp", str(temp))
    camera = world.spawn_actor(camera_bp, carla.Transform(carla.Location(z=1.5)), attach_to=vehicle)
    
    # 保存图片
    def save_image(image, level=level):
        array = np.frombuffer(image.raw_data, dtype=np.uint8).reshape((image.height, image.width, 4))
        array = array[:, :, [2, 1, 0]]  # BGRA -> RGB
        filename = f"./images/color_cast_{level_names[level]}.png"
        Image.fromarray(array).save(filename)
        print(f"Saved: {filename}")
    
    camera.listen(save_image)
    
    # 采集1帧
    world.tick()
    
    camera.destroy()
    vehicle.destroy()

print("Done!")
