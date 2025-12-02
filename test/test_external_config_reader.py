import unittest
import tempfile
import os
import yaml
import json
from types import NoneType

from shared.configs.external_config_reader import ExternalConfigReader


class TestExternalConfigReader(unittest.TestCase):
    """ExternalConfigReader 的单元测试"""

    def setUp(self):
        """测试前的准备工作"""
        self.test_config = {
            'foo': {
                'bar': 'value1',
                'baz': 42,
                'nested': {
                    'deep': {
                        'value': 3.14
                    }
                }
            },
            'number': 100,
            'float_value': 3.14159,
            'bool_true': True,
            'bool_false': False,
            'string_number': '123',
            'string_float': '45.67',
            'bool_string_true': 'true',
            'bool_string_false': 'false',
            'empty': None
        }
        self.reader = ExternalConfigReader(self.test_config)

    def test_init(self):
        """测试初始化"""
        reader = ExternalConfigReader({'key': 'value'})
        self.assertEqual(reader._config, {'key': 'value'})

    def test_get_simple_path(self):
        """测试简单路径查找"""
        self.assertEqual(self.reader.get('number'), 100)
        self.assertEqual(self.reader.get('foo/bar'), 'value1')

    def test_get_nested_path(self):
        """测试嵌套路径查找"""
        self.assertEqual(self.reader.get('foo/nested/deep/value'), 3.14)

    def test_get_path_with_leading_slash(self):
        """测试路径前导斜杠"""
        self.assertEqual(self.reader.get('/number'), 100)
        self.assertEqual(self.reader.get('/foo/bar'), 'value1')

    def test_get_path_with_trailing_slash(self):
        """测试路径尾随斜杠"""
        self.assertEqual(self.reader.get('number/'), 100)
        self.assertEqual(self.reader.get('foo/bar/'), 'value1')

    def test_get_path_with_both_slashes(self):
        """测试路径前后都有斜杠"""
        self.assertEqual(self.reader.get('/number/'), 100)
        self.assertEqual(self.reader.get('/foo/bar/'), 'value1')

    def test_get_empty_route(self):
        """测试空路径"""
        result = self.reader.get('', default='default_value')
        self.assertEqual(result, 'default_value')

    def test_get_not_found_with_default(self):
        """测试找不到配置项时返回默认值"""
        self.assertEqual(self.reader.get('nonexistent', default='default'), 'default')
        self.assertEqual(self.reader.get('foo/nonexistent', default=999), 999)
        self.assertEqual(self.reader.get('nonexistent/deep', default=None), None)

    def test_get_not_found_raises_exception(self):
        """测试找不到配置项时抛出异常"""
        with self.assertRaises(KeyError) as context:
            self.reader.get('nonexistent')
        self.assertIn('Config item not found', str(context.exception))
        self.assertIn('nonexistent', str(context.exception))

        with self.assertRaises(KeyError):
            self.reader.get('foo/nonexistent')

    def test_get_type_conversion_int(self):
        """测试整数类型转换"""
        # 已经是整数
        result = self.reader.get('number', default=0)
        self.assertEqual(result, 100)
        self.assertIsInstance(result, int)

        # 从浮点数转换
        result = self.reader.get('float_value', default=0)
        self.assertEqual(result, 3)
        self.assertIsInstance(result, int)

        # 从字符串转换
        result = self.reader.get('string_number', default=0)
        self.assertEqual(result, 123)
        self.assertIsInstance(result, int)

    def test_get_type_conversion_float(self):
        """测试浮点数类型转换"""
        # 已经是浮点数
        result = self.reader.get('float_value', default=0.0)
        self.assertEqual(result, 3.14159)
        self.assertIsInstance(result, float)

        # 从整数转换
        result = self.reader.get('number', default=0.0)
        self.assertEqual(result, 100.0)
        self.assertIsInstance(result, float)

        # 从字符串转换
        result = self.reader.get('string_float', default=0.0)
        self.assertEqual(result, 45.67)
        self.assertIsInstance(result, float)

    def test_get_type_conversion_bool(self):
        """测试布尔类型转换"""
        # 已经是布尔值
        result = self.reader.get('bool_true', default=False)
        self.assertEqual(result, True)
        self.assertIsInstance(result, bool)

        result = self.reader.get('bool_false', default=True)
        self.assertEqual(result, False)
        self.assertIsInstance(result, bool)

        # 从字符串转换 - true 变体
        for true_str in ['true', 'True', 'TRUE', '1', 'yes', 'Yes', 'YES', 'y', 'Y', 't', 'T']:
            config = {'test': true_str}
            reader = ExternalConfigReader(config)
            result = reader.get('test', default=False)
            self.assertEqual(result, True, f"Failed for '{true_str}'")
            self.assertIsInstance(result, bool)

        # 从字符串转换 - false 变体
        for false_str in ['false', 'False', 'FALSE', '0', 'no', 'No', 'NO', 'n', 'N', 'f', 'F']:
            config = {'test': false_str}
            reader = ExternalConfigReader(config)
            result = reader.get('test', default=True)
            self.assertEqual(result, False, f"Failed for '{false_str}'")
            self.assertIsInstance(result, bool)

    def test_get_type_conversion_str(self):
        """测试字符串类型转换"""
        result = self.reader.get('number', default='')
        self.assertEqual(result, '100')
        self.assertIsInstance(result, str)

        result = self.reader.get('float_value', default='')
        self.assertEqual(result, '3.14159')
        self.assertIsInstance(result, str)

    def test_get_type_conversion_none(self):
        """测试 None 类型转换（不转换）"""
        result = self.reader.get('empty', default=None)
        self.assertIsNone(result)

        # NoneType 作为默认值时，不进行类型转换
        result = self.reader.get('number', default=None)
        self.assertEqual(result, 100)  # 保持原值，不转换为 None

    def test_get_no_type_conversion_when_raise_exception(self):
        """测试使用 RAISE_EXCEPTION 时不进行类型转换"""
        result = self.reader.get('number')
        self.assertEqual(result, 100)
        self.assertIsInstance(result, int)

        result = self.reader.get('foo/bar')
        self.assertEqual(result, 'value1')
        self.assertIsInstance(result, str)

    def test_type_convert_none(self):
        """测试 _type_convert 处理 NoneType"""
        result = self.reader._type_convert('any_value', NoneType)
        self.assertEqual(result, 'any_value')

    def test_type_convert_bool_invalid(self):
        """测试 _type_convert 处理无效的布尔值"""
        with self.assertRaises(ValueError) as context:
            self.reader._type_convert('invalid', bool)
        self.assertIn('Invalid boolean value', str(context.exception))

        with self.assertRaises(ValueError):
            self.reader._type_convert(123, bool)

    def test_type_convert_int_invalid(self):
        """测试 _type_convert 处理无效的整数值"""
        with self.assertRaises(ValueError) as context:
            self.reader._type_convert('not_a_number', int)
        self.assertIn('Invalid integer value', str(context.exception))

        with self.assertRaises(ValueError):
            self.reader._type_convert([1, 2, 3], int)

    def test_type_convert_float_invalid(self):
        """测试 _type_convert 处理无效的浮点数值"""
        with self.assertRaises(ValueError) as context:
            self.reader._type_convert('not_a_number', float)
        self.assertIn('Invalid float value', str(context.exception))

        with self.assertRaises(ValueError):
            self.reader._type_convert([1, 2, 3], float)

    def test_from_yaml(self):
        """测试从 YAML 文件创建实例"""
        test_data = {
            'key1': 'value1',
            'key2': {
                'nested': 42
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data, f)
            temp_path = f.name

        try:
            reader = ExternalConfigReader.from_yaml(temp_path)
            self.assertEqual(reader.get('key1'), 'value1')
            self.assertEqual(reader.get('key2/nested'), 42)
        finally:
            os.unlink(temp_path)

    def test_from_json(self):
        """测试从 JSON 文件创建实例"""
        test_data = {
            'key1': 'value1',
            'key2': {
                'nested': 42
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            reader = ExternalConfigReader.from_json(temp_path)
            self.assertEqual(reader.get('key1'), 'value1')
            self.assertEqual(reader.get('key2/nested'), 42)
        finally:
            os.unlink(temp_path)

    def test_complex_nested_structure(self):
        """测试复杂的嵌套结构"""
        complex_config = {
            'level1': {
                'level2': {
                    'level3': {
                        'level4': {
                            'value': 'deep_value'
                        }
                    }
                }
            }
        }
        reader = ExternalConfigReader(complex_config)
        self.assertEqual(reader.get('level1/level2/level3/level4/value'), 'deep_value')

    def test_mixed_types_in_config(self):
        """测试配置中混合类型"""
        mixed_config = {
            'int': 42,
            'float': 3.14,
            'str': 'hello',
            'bool': True,
            'none': None,
            'list': [1, 2, 3],
            'dict': {'nested': 'value'}
        }
        reader = ExternalConfigReader(mixed_config)

        # 测试各种类型的获取
        self.assertEqual(reader.get('int'), 42)
        self.assertEqual(reader.get('float'), 3.14)
        self.assertEqual(reader.get('str'), 'hello')
        self.assertEqual(reader.get('bool'), True)
        self.assertIsNone(reader.get('none'))
        self.assertEqual(reader.get('list'), [1, 2, 3])
        self.assertEqual(reader.get('dict/nested'), 'value')


if __name__ == '__main__':
    unittest.main()

