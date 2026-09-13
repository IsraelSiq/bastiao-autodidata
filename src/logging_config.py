"""ConfiguraÃ§Ã£o de logging para o BastiÃ£o Autodidata."""

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logging(
    log_dir: str = "logs",
    log_level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """Configura logging com file handler rotativo.

    Args:
        log_dir: DiretÃ³rio para logs
        log_level: NÃ¬vel de logging
        max_bytes: Tamanho mÃ¡ximo do arquivo de log
        backup_count: NÃºmero de backups

    Returns:
        Logger configurado
    """
    # Cria diretÃ³rio de logs
    os.makedirs(log_dir, exist_ok=True)

    # Nome do arquivo com data
    log_file = os.path.join(log_dir, f"bastiao_{datetime.now().strftime('%Y%m%d')}.log")

    # Configura logger root
    logger = logging.getLogger("bastiao")
    logger.setLevel(log_level)

    # Clear handlers
    logger.handlers = []

    # File handler (rotativo)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # JSON formatter para mÃ©tricas (opcional)
    json_formatter = logging.Formatter(
        '{"timestamp":"%(asctime)s","logger":"%(name)s","level":"%(levelname)s","message":"%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # File handler para mÃ©tricas (JSON)
    metrics_file = os.path.join(log_dir, f"metrics_{datetime.now().strftime('%Y%m%d')}.jsonl")
    metrics_handler = RotatingFileHandler(
        metrics_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    metrics_handler.setLevel(logging.INFO)
    metrics_handler.setFormatter(json_formatter)

    # Logger especÃ¬fico para mÃ©tricas
    metrics_logger = logging.getLogger("bastiao.metrics")
    metrics_logger.addHandler(metrics_handler)
    metrics_logger.propagate = False

    logger.info(f"Logging initialized: {log_file}")

    return logger


def get_logger(name: str = "bastiao") -> logging.Logger:
    """Retorna logger configurado.

    Args:
        name: Nome do logger

    Returns:
        Logger
    """
    return logging.getLogger(name)


# Exemplo de uso
if __name__ == "__main__":
    logger = setup_logging()
    logger.info("Test log message")
    logger.warning("Test warning")
    logger.error("Test error")

    metrics = get_logger("bastiao.metrics")
    metrics.info('{"event":"test","value":42}')
