import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    """应用级日志配置，应在导入业务模块前调用一次。"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("agent.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )
