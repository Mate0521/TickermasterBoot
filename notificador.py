"""
Módulo de notificaciones para TicketmasterBot.

Envía alertas a Telegram con mecanismo de reintento (retry)
y backoff exponencial ante fallos de red.
"""

import logging
import time

import requests

import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("ticketmaster.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def enviar_alerta(mensaje: str, chat_id: str | None = None) -> bool:
    """
    Envía un mensaje de alerta a Telegram vía Bot API.

    Implementa reintentos con backoff exponencial (2^intento segundos).
    Retorna True si se envió con éxito, False si fallaron todos los intentos.
    """
    chat_id = chat_id or config.TELEGRAM_CHAT_ID
    if not chat_id:
        logger.warning("Telegram chat_id no configurado")
        return False

    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensaje,
    }

    for intento in range(1, config.TELEGRAM_RETRIES + 1):
        try:
            response = requests.get(url, params=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Alerta enviada correctamente a Telegram")
                return True

            logger.warning(
                "Telegram respondió con código %s (intento %s/%s)",
                response.status_code,
                intento,
                config.TELEGRAM_RETRIES,
            )

        except (requests.ConnectionError, requests.Timeout) as e:
            logger.warning(
                "Error de red al enviar alerta (intento %s/%s): %s",
                intento,
                config.TELEGRAM_RETRIES,
                e,
            )

        if intento < config.TELEGRAM_RETRIES:
            espera = 2**intento
            logger.info("Reintentando en %s segundos...", espera)
            time.sleep(espera)

    logger.critical(
        "No se pudo enviar la alerta a Telegram después de %s intentos",
        config.TELEGRAM_RETRIES,
    )
    return False
