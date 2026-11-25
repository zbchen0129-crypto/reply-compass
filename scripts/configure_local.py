"""One-time interactive credential setup; secrets never become command arguments."""
import getpass
import os
from pathlib import Path
import sys
import tempfile
import warnings
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from local_config import ENV_PATH, ConfigError, parse_env


def save_config(key, model, path=ENV_PATH):
    if not key or not model or any(c.isspace() or ord(c) < 32 or ord(c) == 127 or c in '\"\'' for c in key + model):
        raise ConfigError('密钥和模型名称不能为空，且不能包含空白、引号或控制字符。')
    if path.is_symlink():
        raise ConfigError('拒绝覆盖符号链接，请使用普通 .env 文件。')
    values = parse_env(path.read_text()) if path.exists() else {}
    values.update(OPENAI_API_KEY=key, OPENAI_MODEL=model)
    fd, temporary = tempfile.mkstemp(prefix='.env.', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write('# Local credentials; never commit this file.\n')
            for name, value in values.items():
                stream.write(f'{name}={value}\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    if not sys.stdin.isatty():
        raise SystemExit('请在本机交互式终端运行此命令，不要通过聊天或命令参数传入密钥。')
    print('密钥将保存到项目 .env（本机明文文件，仅当前用户可读写，不提交 Git）。')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            key = getpass.getpass('粘贴 OpenAI API Key，按回车（输入不可见）：').strip()
        model = input('模型名称 [gpt-4.1-mini]：').strip() or 'gpt-4.1-mini'
        save_config(key, model)
    except (ConfigError, OSError, UnicodeError, getpass.GetPassWarning):
        raise SystemExit('未保存配置。请检查输入格式、隐藏输入支持及文件权限。') from None
    except (EOFError, KeyboardInterrupt):
        raise SystemExit('\n配置已取消。') from None
    print('配置已保存，密钥未显示。重启服务后生效。')


if __name__ == '__main__':
    main()
