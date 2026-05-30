"""
Orquestador principal de TicketmasterBot.

Ejecuta el ciclo infinito de monitoreo, alterna entre API oficial
y scraping de respaldo (failover), y envía alertas por Telegram.
"""

import logging
import time

import config
from monitor_api import verificar_estado_api
from monitor_scraping import verificar_estado_scraping
from notificador import enviar_alerta

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


def main():
    logger.info("=" * 50)
    logger.info("TicketmasterBot iniciado - Monitoreo híbrido 24/7")
    logger.info("=" * 50)

    contador_fallos_api = 0

    if not config.API_DISPONIBLE:
        logger.warning(
            "Modo scraping únicamente (API no configurada). "
            "Establece TICKETMASTER_API_KEY y TICKETMASTER_EVENT_ID "
            "en .env para activar el modo híbrido."
        )

    while True:
        try:
            if (
                config.API_DISPONIBLE
                and contador_fallos_api < config.MAX_API_FAILURES
            ):
                exito, hay_boletas = verificar_estado_api()

                if exito:
                    contador_fallos_api = 0
                    if hay_boletas:
                        enviar_alerta(
                            "🚨 ¡ALERTA! Posibles boletas disponibles para BTS. "
                            "Revisa la página de inmediato: "
                            + config.EVENT_URL_SCRAPING
                        )
                else:
                    contador_fallos_api += 1
                    logger.warning(
                        "Fallo en API (%s/%s)",
                        contador_fallos_api,
                        config.MAX_API_FAILURES,
                    )

                time.sleep(config.API_DELAY)

            else:
                if config.API_DISPONIBLE:
                    logger.warning(
                        "Failover: cambiando a scraping tras %s fallos de API",
                        contador_fallos_api,
                    )
                else:
                    logger.info("Usando scraping como modo principal")

                exito, hay_boletas = verificar_estado_scraping()

                if exito:
                    contador_fallos_api = 0
                    if hay_boletas:
                        enviar_alerta(
                            "🚨 ¡ALERTA SCRAPER! Posibles boletas disponibles "
                            "para BTS. Entra ya: " + config.EVENT_URL_SCRAPING
                        )
                else:
                    logger.error("Ambos sistemas de monitoreo fallaron")
                    enviar_alerta(
                        "⚠️ Ambos sistemas de monitoreo fallaron "
                        "(API y Scraping). Revisa el servidor."
                    )
                    time.sleep(60)

        except Exception as e:
            logger.critical("Error crítico no manejado: %s", e)
            enviar_alerta(
                "🔥 ERROR CRÍTICO en TicketmasterBot: "
                f"{e}. El bot se recuperará en 60 segundos."
            )
            time.sleep(60)


if __name__ == "__main__":
    main()
