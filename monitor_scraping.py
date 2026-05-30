"""
Módulo de monitoreo por web scraping (fallback).

Utiliza Playwright en modo headless con User-Agent variable,
jitter y búsqueda por texto en el DOM para detectar
disponibilidad de boletas.
"""

import logging
import random
import time

from playwright.sync_api import sync_playwright

import config

logger = logging.getLogger(__name__)

ultimo_estado_scraping: str | None = None

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

KLAVS_AGOTADO = ["agotado", "sold out", "no tickets available", "entradas agotadas"]


def _texto_agotado_presente(page) -> bool:
    """Busca en el cuerpo de la página si hay texto de entradas agotadas."""
    body = page.locator("body").inner_text(timeout=10_000).lower()
    for klav in KLAVS_AGOTADO:
        if klav in body:
            return True
    return False


def verificar_estado_scraping() -> tuple[bool, bool]:
    """
    Navega a la URL del evento con Playwright y verifica disponibilidad.

    Retorna:
        (exito_de_peticion, hay_nuevas_boletas)
    """
    global ultimo_estado_scraping

    try:
        with sync_playwright() as pw:
            navegador = pw.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            contexto = navegador.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
            )
            pagina = contexto.new_page()

            logger.info("Navegando a %s ...", config.EVENT_URL_SCRAPING)
            pagina.goto(config.EVENT_URL_SCRAPING, timeout=30_000)

            time.sleep(random.uniform(3.0, 7.0))

            agotado = _texto_agotado_presente(pagina)

            navegador.close()

        if not agotado:
            estado_actual = "disponible"
            if (
                ultimo_estado_scraping is not None
                and ultimo_estado_scraping != estado_actual
            ):
                logger.info(
                    "¡Boletas disponibles detectadas! (estado anterior: %s)",
                    ultimo_estado_scraping,
                )
                ultimo_estado_scraping = estado_actual
                return (True, True)

            if ultimo_estado_scraping is None:
                ultimo_estado_scraping = estado_actual
                logger.info("Estado inicial (scraping): disponible")

            return (True, False)

        estado_actual = "agotado"
        if ultimo_estado_scraping is None:
            ultimo_estado_scraping = estado_actual
            logger.info("Estado inicial (scraping): agotado")
        elif ultimo_estado_scraping != estado_actual:
            ultimo_estado_scraping = estado_actual
            logger.info("Estado cambiado a: agotado")

        return (True, False)

    except Exception as e:
        logger.error("Error en scraping (posible bloqueo): %s", e)
        return (False, False)
