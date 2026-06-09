"""
Orquestador principal de TicketmasterBot multicliente.

Carga la lista de clientes desde clientes.json y ejecuta el ciclo
de monitoreo para cada uno, con failover API -> scraping.
Alertas envían al canal correspondiente (Telegram y/o WhatsApp).
"""

import logging
import time

import config
from monitor_multicliente import cargar_clientes, ejecutar_ciclo

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

DELAY = config.API_DELAY


def main():
    logger.info("=" * 50)
    logger.info("TicketmasterBot iniciado - Monitoreo multicliente")
    logger.info("=" * 50)

    clientes = cargar_clientes()
    if not clientes:
        logger.error("No hay clientes habilitados en clientes.json")
        logger.info("Esperando 60s antes de reintentar...")
        time.sleep(60)

    logger.info("Clientes cargados: %s", len(clientes))
    for cli in clientes:
        logger.info(
            "  - %s (API: %s, Telegram: %s, WhatsApp: %s)",
            cli.nombre,
            "si" if cli.api_disponible else "no",
            "si" if cli.telegram_chat_id else "no",
            "si" if cli.whatsapp_chat_id else "no",
        )

    while True:
        try:
            ejecutar_ciclo(clientes)
            time.sleep(DELAY)
        except Exception as e:
            logger.critical("Error crítico: %s", e, exc_info=True)
            time.sleep(60)


if __name__ == "__main__":
    main()
