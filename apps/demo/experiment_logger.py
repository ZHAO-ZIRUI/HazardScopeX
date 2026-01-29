import csv
import os

class ExperimentLogger:
    def __init__(self, filename="experiment_results.csv"):
        self.filename = filename
        # 核心九个因子
        self.factors = [
            'Rain', 'Fog', 'Dust', 
            'OverExposure', 'UnderExposure', 
            'ChromaticAberration', 'ColorCast', 
            'Time', 'CarLight'
        ]
        
        # 重新设计的表头：
        # 1. 基础信息
        # 2. 组合描述 (如 Fog&Rain&Dust, 213)
        # 3. 展平的因子列 (便于机器学习直接训练)
        # 4. 评价指标
        self.header = [
            'scenario_name', 'speed', 'repeat',
            'factor_combination',  # 因子名组合，如 "Fog&Rain&Dust"
            'intensity_level',      # 对应的强度组合，如 "213"
            *self.factors,          # 展平列
            'detect_distance', 'final_distance', 'is_collision'
        ]
        
        if not os.path.exists(self.filename):
            with open(self.filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.header)
                writer.writeheader()

    def log_result(self, scenario, speed, repeat, active_factor_dict, metrics):
        """
        保存单次实验结果
        :param active_factor_dict: 仅包含本次激活的因子及其强度(1,2,3)，
                                  例如 {'Fog': 2, 'Rain': 1, 'Dust': 3}
        """
        # 1. 构造合并的字符串描述
        # 按字母顺序排序，确保 "Fog&Rain" 和 "Rain&Fog" 统一
        sorted_active_names = sorted(active_factor_dict.keys())
        combo_str = "&".join(sorted_active_names)
        level_str = "".join([str(active_factor_dict[name]) for name in sorted_active_names])

        # 2. 构造基础行数据
        row = {
            'scenario_name': scenario,
            'speed': speed,
            'repeat': repeat,
            'factor_combination': combo_str,
            'intensity_level': level_str
        }
        
        # 3. 填充展平的因子列 (机器学习输入)
        for f in self.factors:
            row[f] = active_factor_dict.get(f, 0) # 未激活则强度为 0
            
        # 4. 填充评价指标
        row.update(metrics)
        
        with open(self.filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.header)
            writer.writerow(row)

# ==========================================
# 采样逻辑调用示例
# ==========================================
if __name__ == "__main__":
    logger = ExperimentLogger("driving_safety_data_v2.csv")
    
    # 模拟一次“九选三”实验
    # 假设本次抽中了 Fog, Rain, Dust，强度分别为 2, 1, 3
    current_active_factors = {
        'Fog': 2,
        'Rain': 1,
        'Dust': 3
    }
    
    current_metrics = {
        'detect_distance': 28.5,
        'final_distance': 5.2,
        'is_collision': False
    }
    
    logger.log_result(
        scenario="Front vehicle keep stop",
        speed=60.0,
        repeat=0,
        active_factor_dict=current_active_factors,
        metrics=current_metrics
    )
    
    print(f"实验数据已记录。组合: Fog&Rain&Dust, 强度: 213")