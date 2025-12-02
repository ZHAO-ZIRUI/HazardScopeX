import unittest
import tempfile
import os
import yaml
import json
from dataclasses import dataclass, field

from shared.configs.abstract_config import AbstractConfig
from shared.configs.external_config_reader import ExternalConfigReader


@dataclass
class SampleConfig(AbstractConfig):
    """测试用的配置类"""
    str_field: str = field(default='default_str', metadata={'route': 'test/str'})
    int_field: int = field(default=100, metadata={'route': 'test/int'})
    float_field: float = field(default=3.14, metadata={'route': 'test/float'})
    bool_field: bool = field(default=True, metadata={'route': 'test/bool'})
    no_route_field: str = field(default='no_route')  # 没有 route 的字段
    nested_field: str = field(default='nested_default', metadata={'route': 'test/nested/deep/value'})


class TestAbstractConfig(unittest.TestCase):
    """AbstractConfig 的单元测试"""

    def setUp(self):
        """测试前的准备工作"""
        self.test_config_dict = {
            'test': {
                'str': 'loaded_str',
                'int': 200,
                'float': 6.28,
                'bool': False,
                'nested': {
                    'deep': {
                        'value': 'nested_loaded'
                    }
                }
            }
        }

    def test_load_from_yaml_file(self):
        """测试从 YAML 文件加载配置"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(self.test_config_dict, f)
            temp_path = f.name

        try:
            config = SampleConfig.load(temp_path)
            self.assertEqual(config.str_field, 'loaded_str')
            self.assertEqual(config.int_field, 200)
            self.assertEqual(config.float_field, 6.28)
            self.assertEqual(config.bool_field, False)
            self.assertEqual(config.nested_field, 'nested_loaded')
            self.assertEqual(config.no_route_field, 'no_route')  # 没有 route，保持默认值
        finally:
            os.unlink(temp_path)

    def test_load_from_json_file(self):
        """测试从 JSON 文件加载配置"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_config_dict, f)
            temp_path = f.name

        try:
            config = SampleConfig.load(temp_path)
            self.assertEqual(config.str_field, 'loaded_str')
            self.assertEqual(config.int_field, 200)
            self.assertEqual(config.float_field, 6.28)
            self.assertEqual(config.bool_field, False)
            self.assertEqual(config.nested_field, 'nested_loaded')
        finally:
            os.unlink(temp_path)

    def test_load_from_external_config_reader(self):
        """测试从 ExternalConfigReader 实例加载配置"""
        reader = ExternalConfigReader(self.test_config_dict)
        config = SampleConfig.load(reader)
        
        self.assertEqual(config.str_field, 'loaded_str')
        self.assertEqual(config.int_field, 200)
        self.assertEqual(config.float_field, 6.28)
        self.assertEqual(config.bool_field, False)
        self.assertEqual(config.nested_field, 'nested_loaded')
        self.assertEqual(config.no_route_field, 'no_route')

    def test_load_with_default_values(self):
        """测试使用默认值的情况"""
        empty_config = {}
        reader = ExternalConfigReader(empty_config)
        config = SampleConfig.load(reader)
        
        self.assertEqual(config.str_field, 'default_str')
        self.assertEqual(config.int_field, 100)
        self.assertEqual(config.float_field, 3.14)
        self.assertEqual(config.bool_field, True)
        self.assertEqual(config.nested_field, 'nested_default')
        self.assertEqual(config.no_route_field, 'no_route')

    def test_load_partial_config(self):
        """测试部分配置覆盖默认值"""
        partial_config = {
            'test': {
                'str': 'partial_str',
                'int': 300
                # 其他字段使用默认值
            }
        }
        reader = ExternalConfigReader(partial_config)
        config = SampleConfig.load(reader)
        
        self.assertEqual(config.str_field, 'partial_str')
        self.assertEqual(config.int_field, 300)
        self.assertEqual(config.float_field, 3.14)  # 使用默认值
        self.assertEqual(config.bool_field, True)  # 使用默认值
        self.assertEqual(config.nested_field, 'nested_default')  # 使用默认值

    def test_load_invalid_path_raises_error(self):
        """测试无效路径抛出异常"""
        with self.assertRaises(ValueError) as context:
            SampleConfig.load('invalid.txt')
        self.assertIn('Invalid config path or reader', str(context.exception))

        with self.assertRaises(ValueError) as context:
            SampleConfig.load(123)  # 非字符串非 reader
        self.assertIn('Invalid config path or reader', str(context.exception))

    def test_load_nonexistent_file_raises_error(self):
        """测试不存在的文件抛出异常"""
        with self.assertRaises(FileNotFoundError):
            SampleConfig.load('nonexistent.yaml')

        with self.assertRaises(FileNotFoundError):
            SampleConfig.load('nonexistent.json')

    def test_override_from_reader(self):
        """测试 _override_from_reader 方法"""
        config = SampleConfig()
        reader = ExternalConfigReader(self.test_config_dict)
        
        # 验证初始默认值
        self.assertEqual(config.str_field, 'default_str')
        self.assertEqual(config.int_field, 100)
        
        # 执行覆盖
        config._override_from_reader(reader)
        
        # 验证覆盖后的值
        self.assertEqual(config.str_field, 'loaded_str')
        self.assertEqual(config.int_field, 200)
        self.assertEqual(config.float_field, 6.28)
        self.assertEqual(config.bool_field, False)
        self.assertEqual(config.nested_field, 'nested_loaded')
        self.assertEqual(config.no_route_field, 'no_route')  # 没有 route，不受影响

    def test_override_from_reader_with_missing_fields(self):
        """测试 _override_from_reader 处理缺失字段"""
        config = SampleConfig()
        partial_config = {
            'test': {
                'str': 'new_str'
                # 其他字段缺失
            }
        }
        reader = ExternalConfigReader(partial_config)
        
        config._override_from_reader(reader)
        
        self.assertEqual(config.str_field, 'new_str')
        self.assertEqual(config.int_field, 100)  # 使用默认值
        self.assertEqual(config.float_field, 3.14)  # 使用默认值
        self.assertEqual(config.bool_field, True)  # 使用默认值

    def test_override_from_reader_with_none_route(self):
        """测试 _override_from_reader 处理 route 为 None 的字段"""
        config = SampleConfig()
        reader = ExternalConfigReader(self.test_config_dict)
        
        config._override_from_reader(reader)
        
        # no_route_field 的 metadata 中没有 route 或 route 为 None，应该保持默认值
        self.assertEqual(config.no_route_field, 'no_route')

    def test_load_returns_same_instance_type(self):
        """测试 load 方法返回正确的实例类型"""
        reader = ExternalConfigReader(self.test_config_dict)
        config = SampleConfig.load(reader)
        
        self.assertIsInstance(config, SampleConfig)
        self.assertIsInstance(config, AbstractConfig)

    def test_multiple_loads_independent(self):
        """测试多次加载配置相互独立"""
        config1_dict = {'test': {'str': 'config1'}}
        config2_dict = {'test': {'str': 'config2'}}
        
        config1 = SampleConfig.load(ExternalConfigReader(config1_dict))
        config2 = SampleConfig.load(ExternalConfigReader(config2_dict))
        
        self.assertEqual(config1.str_field, 'config1')
        self.assertEqual(config2.str_field, 'config2')

    def test_load_with_empty_yaml(self):
        """测试加载空的 YAML 文件"""
        empty_config = {}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(empty_config, f)
            temp_path = f.name

        try:
            config = SampleConfig.load(temp_path)
            # 所有字段应该使用默认值
            self.assertEqual(config.str_field, 'default_str')
            self.assertEqual(config.int_field, 100)
            self.assertEqual(config.float_field, 3.14)
            self.assertEqual(config.bool_field, True)
        finally:
            os.unlink(temp_path)

    def test_load_with_empty_json(self):
        """测试加载空的 JSON 文件"""
        empty_config = {}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(empty_config, f)
            temp_path = f.name

        try:
            config = SampleConfig.load(temp_path)
            # 所有字段应该使用默认值
            self.assertEqual(config.str_field, 'default_str')
            self.assertEqual(config.int_field, 100)
            self.assertEqual(config.float_field, 3.14)
            self.assertEqual(config.bool_field, True)
        finally:
            os.unlink(temp_path)

    def test_override_from_reader_returns_self(self):
        """测试 _override_from_reader 返回自身"""
        config = SampleConfig()
        reader = ExternalConfigReader(self.test_config_dict)
        
        result = config._override_from_reader(reader)
        
        self.assertIs(result, config)

    def test_load_with_complex_nested_structure(self):
        """测试加载复杂的嵌套结构"""
        complex_config = {
            'test': {
                'str': 'simple',
                'nested': {
                    'deep': {
                        'value': 'very_deep_value'
                    }
                }
            }
        }
        reader = ExternalConfigReader(complex_config)
        config = SampleConfig.load(reader)
        
        self.assertEqual(config.str_field, 'simple')
        self.assertEqual(config.nested_field, 'very_deep_value')

    def test_load_with_type_conversion(self):
        """测试配置加载时的类型转换"""
        type_test_config = {
            'test': {
                'int': '500',  # 字符串形式的整数
                'float': '7.77',  # 字符串形式的浮点数
                'bool': 'true'  # 字符串形式的布尔值
            }
        }
        reader = ExternalConfigReader(type_test_config)
        config = SampleConfig.load(reader)
        
        # ExternalConfigReader 会根据 default 参数进行类型转换
        # 但由于我们使用的是 field.default，需要验证实际行为
        self.assertEqual(config.int_field, 500)
        self.assertEqual(config.float_field, 7.77)
        self.assertEqual(config.bool_field, True)


if __name__ == '__main__':
    unittest.main()

