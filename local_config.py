"""Small literal .env loader. No shell evaluation, expansion, or third-party dependency."""
import os
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent / '.env'
ALLOWED = {'OPENAI_API_KEY', 'OPENAI_MODEL', 'PORT'}


class ConfigError(ValueError):
    pass


def parse_env(text):
    values = {}
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        key, separator, value = line.partition('=')
        key, value = key.strip(), value.strip()
        if not separator or key not in ALLOWED or key in values:
            raise ConfigError(f'.env 第 {number} 行字段无效或重复；请检查配置。')
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                raise ConfigError(f'.env 第 {number} 行引号未闭合。')
            value = value[1:-1]
        if any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ConfigError(f'.env 第 {number} 行含无效控制字符。')
        values[key] = value
    return values


def load_env(path=ENV_PATH, environ=None):
    """Read only this project's file; existing environment values take precedence."""
    target = os.environ if environ is None else environ
    if not path.exists():
        return False
    try:
        values = parse_env(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError):
        raise ConfigError('无法读取项目 .env 文件，请检查权限或编码。') from None
    for key, value in values.items():
        target.setdefault(key, value)
    return True
