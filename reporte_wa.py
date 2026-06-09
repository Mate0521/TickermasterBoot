import logging
import time

import requests

import config

logger = logging.getLogger(__name__)


def _obtener_session_id() -> str | None:
    try:
        r = requests.get(
            f"{config.OPENWA_URL}/sessions",
            headers={"X-API-Key": config.OPENWA_API_KEY},
            timeout=10,
        )
        if r.status_code != 200:
            logger.warning("No se pudo listar sesiones OpenWA: %s", r.status_code)
            return None
        for s in r.json():
            if s.get("name") == config.OPENWA_SESSION:
                return s.get("id")
        logger.warning("Sesión '%s' no encontrada", config.OPENWA_SESSION)
        return None
    except (requests.ConnectionError, requests.Timeout) as e:
        logger.warning("Error de red al listar sesiones: %s", e)
        return None


def enviar_reporte_wa(mensaje: str, chat_id: str | None = None) -> bool:
    if not config.OPENWA_DISPONIBLE:
        logger.warning("OpenWA no configurado. Salta alerta WhatsApp.")
        return False

    chat_id = chat_id or config.OPENWA_CHAT_ID
    if not chat_id:
        logger.warning("WhatsApp chat_id no configurado")
        return False

    session_id = _obtener_session_id()
    if not session_id:
        return False

    url = f"{config.OPENWA_URL}/sessions/{session_id}/messages/send-text"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": config.OPENWA_API_KEY,
    }
    payload = {
        "chatId": chat_id,
        "text": mensaje,
    }

    for intento in range(1, config.OPENWA_RETRIES + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code in (200, 201):
                logger.info("Reporte enviado correctamente a WhatsApp")
                return True

            logger.warning(
                "OpenWA respondió %s (intento %s/%s)",
                response.status_code,
                intento,
                config.OPENWA_RETRIES,
            )

        except (requests.ConnectionError, requests.Timeout) as e:
            logger.warning(
                "Error de red al enviar reporte WhatsApp (intento %s/%s): %s",
                intento,
                config.OPENWA_RETRIES,
                e,
            )

        if intento < config.OPENWA_RETRIES:
            espera = 2 ** intento
            logger.info("Reintentando WhatsApp en %s segundos...", espera)
            time.sleep(espera)

    logger.error(
        "No se pudo enviar el reporte a WhatsApp tras %s intentos",
        config.OPENWA_RETRIES,
    )
    return False
