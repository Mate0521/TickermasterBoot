"""
Módulo de monitoreo por API oficial de Ticketmaster.

Consume el endpoint Discovery v2 y detecta cambios en el estado
del evento (dates.status.code) para activar alertas.
"""

import logging

import requests

import config

logger = logging.getLogger(__name__)

ultimo_estado: str | None = None


def verificar_estado_api() -> tuple[bool, bool]:
    """
    Consulta el estado del evento en la API de Ticketmaster.

    Si no hay API key o eventId configurados, retorna (True, False)
    para que el orquestador continúe sin marcar fallos.

    Retorna:
        (exito_de_peticion, hay_nuevas_boletas)
    """
    global ultimo_estado

    if not config.API_DISPONIBLE:
        logger.warning(
            "API no configurada (faltan TICKETMASTER_API_KEY o "
            "TICKETMASTER_EVENT_ID). Saltando fase API."
        )
        return (True, False)

    url = (
        f"{config.API_BASE_URL}"
        f"{config.TICKETMASTER_EVENT_ID}.json"
        f"?apikey={config.TICKETMASTER_API_KEY}"
    )

    try:
        response = requests.get(url, timeout=15)
        status_code = response.status_code

        if status_code == 200:
            datos = response.json()
            estado_actual = (
                datos.get("dates", {})
                .get("status", {})
                .get("code", "desconocido")
            )

            if ultimo_estado is not None and ultimo_estado != estado_actual:
                if estado_actual == "onsale":
                    logger.info(
                        "¡Cambio detectado! Estado anterior: %s → nuevo: %s",
                        ultimo_estado,
                        estado_actual,
                    )
                    ultimo_estado = estado_actual
                    return (True, True)

                logger.info(
                    "Cambio de estado: %s → %s (sin boletas nuevas)",
                    ultimo_estado,
                    estado_actual,
                )
                ultimo_estado = estado_actual
                return (True, False)

            if ultimo_estado is None:
                ultimo_estado = estado_actual
                logger.info("Estado inicial registrado: %s", estado_actual)

            return (True, False)

        if status_code == 429:
            logger.warning(
                "Límite de tasa excedido (HTTP %s)", status_code
            )
            return (False, False)

        if status_code in (401, 403):
            logger.error(
                "Error de autenticación o baneo (HTTP %s)", status_code
            )
            return (False, False)

        logger.warning(
            "Código HTTP inesperado: %s", status_code
        )
        return (False, False)

    except requests.exceptions.RequestException as e:
        logger.error(
            "Error de red o timeout al consultar API: %s", e
        )
        return (False, False)
