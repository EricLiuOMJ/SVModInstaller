import logging
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass  # 可以移除，如果 Colors 也不再需要

# --- 移除 Colors dataclass，直接定义常量 ---
# 如果其他地方没有用到 Colors.XXX，可以直接移除 Colors 类
# 如果用到了，保留 Colors 类或者也改成常量
COLOR_RESET = '\033[0m'
COLOR_RED = '\033[91m'
COLOR_GREEN = '\033[92m'
COLOR_YELLOW = '\033[93m'
COLOR_BLUE = '\033[94m'
COLOR_MAGENTA = '\033[95m'
COLOR_CYAN = '\033[96m'
COLOR_WHITE = '\033[97m'
COLOR_BOLD = '\033[1m'
COLOR_UNDERLINE = '\033[4m'
# ENDC = '\033[0m' # 重复了 RESET

# --- 定义和注册自定义日志级别 (保持不变) ---
LOG_LEVEL_SUCCESS = logging.WARNING + 5
LOG_LEVEL_STEP = logging.INFO + 5
LOG_LEVEL_TRACE = logging.DEBUG + 5
logging.addLevelName(LOG_LEVEL_SUCCESS, "SUCCESS")
logging.addLevelName(LOG_LEVEL_STEP, "STEP")
logging.addLevelName(LOG_LEVEL_TRACE, "TRACE")

# --- 定义格式化字符串常量 (替换 FormatStrings dataclass) ---
FILE_FMT = '%(asctime)s - [%(levelname)s] - [%(name)s:%(filename)s:%(lineno)d] - %(message)s'
CONSOLE_FMT = '[%(levelname)-8s] - [%(filename)s:%(lineno)d]  %(message)s'
EXE_FMT = '[%(levelname)-8s] - %(message)s'

# --- 自定义控制台 Formatter ---


class ColorConsoleFormatter(logging.Formatter):
    """自定义 Formatter，为控制台日志添加颜色"""

    LEVEL_COLORS = {
        LOG_LEVEL_TRACE: COLOR_MAGENTA,
        logging.DEBUG: COLOR_GREEN,
        logging.INFO: COLOR_CYAN,
        LOG_LEVEL_STEP: COLOR_BLUE,
        LOG_LEVEL_SUCCESS: COLOR_GREEN + COLOR_BOLD,
        logging.WARNING: COLOR_YELLOW,
        logging.ERROR: COLOR_RED,
        logging.CRITICAL: COLOR_RED + COLOR_BOLD,
    }

    def format(self, record):
        log_message = super().format(record)
        level_color = self.LEVEL_COLORS.get(record.levelno, COLOR_WHITE)
        # 移除末尾可能存在的换行符，避免颜色重置影响下一行
        log_message = log_message.rstrip('\n\r')
        colored_message = f"{level_color}{log_message}{COLOR_RESET}"
        # 如果原始消息包含换行符，在这里重新添加，确保多行日志正确显示
        if hasattr(record, 'message') and '\n' in record.message:
            # 简单的处理方式，可能需要根据具体日志格式调整
            colored_message += '\n'
        return colored_message


class ColorLogger:
    """
    一个提供彩色控制台输出和文件日志记录的日志类。
    """
    # 将默认格式移到类外部作为常量

    def __init__(self, name="SVModInstallerApp", level=LOG_LEVEL_TRACE, console_format=EXE_FMT, file_format=FILE_FMT):
        """
        初始化 Logger。

        Args:
            name (str): Logger 的名称。
            level (int): Logger 处理的最低级别。
            console_format (str): 控制台输出格式字符串。
            file_format (str): 文件输出格式字符串。
        """
        self.logger = logging.getLogger(name)
        # 避免重复添加 handlers
        if self.logger.hasHandlers():
            self.logger.handlers.clear()  # 清除现有 handlers

        self.logger.setLevel(level)
        self.logger.propagate = False  # 通常建议设置，避免向 root logger 传递

        # --- 确定基础路径和日志目录 ---
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent.parent.resolve()

        log_dir = base_path / "logs"
        try:
            log_dir.mkdir(parents=True, exist_ok=True)  # 添加 parents=True
        except OSError as e:
            sys.stderr.write(f"无法创建日志目录 {log_dir}: {e}\n")
            self._add_console_handler(level, console_format)  # 至少保留控制台输出
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"{name}_{timestamp}.log"  # 使用 logger 名称区分日志文件

        # --- 添加文件 Handler ---
        self._add_file_handler(level, file_format, log_file)

        # --- 添加控制台 Handler ---
        self._add_console_handler(level, console_format)

        self.logger.log(
            LOG_LEVEL_TRACE, f"Logger '{name}' initialized. Level: {logging.getLevelName(level)}. Log file: {log_file if 'log_file' in locals() else 'N/A'}")

    def _add_file_handler(self, level, file_format, log_file):
        """添加文件处理器"""
        try:
            file_formatter = logging.Formatter(file_format)
            file_handler = logging.FileHandler(
                log_file, encoding='utf-8', mode='a')
            file_handler.setLevel(level)
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            self.logger.error(f"无法添加文件日志处理器: {e}", exc_info=True)

    def _add_console_handler(self, level, console_format):
        """添加控制台处理器"""
        try:
            console_formatter = ColorConsoleFormatter(console_format)
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        except Exception as e:
            # 如果控制台处理器也失败，至少尝试打印到 stderr
            sys.stderr.write(f"无法添加控制台日志处理器: {e}\n")

    def trace(self, text: str) -> None:
        """记录 TRACE 级别的日志"""
        self.logger.log(LOG_LEVEL_TRACE, text, stacklevel=2)

    def debug(self, text: str) -> None:
        """记录 DEBUG 级别的日志"""
        self.logger.debug(text, stacklevel=2)

    def info(self, text: str) -> None:
        """记录 INFO 级别的日志"""
        self.logger.info(text, stacklevel=2)

    def step(self, text: str) -> None:
        """记录 STEP 级别的日志"""
        self.logger.log(LOG_LEVEL_STEP, text, stacklevel=2)

    def success(self, text: str) -> None:
        """记录 SUCCESS 级别的日志"""
        self.logger.log(LOG_LEVEL_SUCCESS, text, stacklevel=2)

    def warning(self, text: str) -> None:
        """记录 WARNING 级别的日志"""
        self.logger.warning(text, stacklevel=2)

    def error(self, text: str) -> None:
        """记录 ERROR 级别的日志"""
        self.logger.error(text, stacklevel=2)

    def critical(self, text: str) -> None:
        """记录 CRITICAL 级别的日志"""
        self.logger.critical(text, stacklevel=2)


# --- 在模块级别创建默认 Logger 实例 ---
# 使用默认格式常量
default_logger = ColorLogger(name="SVModApps", level=logging.DEBUG,
                             console_format=EXE_FMT, file_format=FILE_FMT)

# --- 导出默认 logger ---
logger = default_logger
