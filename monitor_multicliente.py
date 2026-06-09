import json
import logging
import time

import requests

import config
from monitor_api import verificar_estado_api as _check_api
from monitor_scraping import verificar_estado_scraping as _check_scraping
from notificador import enviar_alerta
from reporte_wa import enviar_reporte_wa

logger = logging.getLogger(__name__)

RUTA_CLIENTES = "clientes.json"


class MonitorCliente:
    def __init__(self, cfg: dict):
        self.nombre = cfg["nombre"]
        self.evento_id = cfg.get("evento_id", "") or ""
        self.url_scraping = cfg.get("url_scraping", "")
        self.telegram_chat_id = cfg.get("telegram_chat_id") or None
        self.whatsapp_chat_id = cfg.get("whatsapp_chat_id") or None
        self.habilitado = cfg.get("habilitado", True)

        self.api_disponible = bool(config.TICKETMASTER_API_KEY and self.evento_id)
        self._ultimo_estado_api: str | None = None
        self._ultimo_estado_scraping: str | None = None
        self._contador_fallos_api = 0

    def verificar_api(self) -> tuple[bool, bool]:
        if not self.api_disponible:
            return (True, False)

        url = (
            f"{config.API_BASE_URL}"
            f"{self.evento_id}.json"
            f"?apikey={config.TICKETMASTER_API_KEY}"
        )
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json()
                estado = (
                    data.get("dates", {})
                    .get("status", {})
                    .get("code", "desconocido")
                )

                if self._ultimo_estado_api is not None and self._ultimo_estado_api != estado:
                    if estado == "onsale":
                        self._ultimo_estado_api = estado
                        return (True, True)
                    self._ultimo_estado_api = estado
                    return (True, False)

                if self._ultimo_estado_api is None:
                    self._ultimo_estado_api = estado
                    logger.info(
                        "[%s] Estado inicial API: %s", self.nombre, estado
                    )
                return (True, False)

            if r.status_code in (429, 401, 403):
                return (False, False)
            return (False, False)

        except requests.exceptions.RequestException:
            return (False, False)

    def verificar_scraping(self) -> tuple[bool, bool]:
        if not self.url_scraping:
            return (True, False)

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as pw:
                nav = pw.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                    ],
                )
                ctx = nav.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1920, "height": 1080},
                )
                page = ctx.new_page()
                logger.info("[%s] Scraping %s ...", self.nombre, self.url_scraping)
                page.goto(self.url_scraping, timeout=30_000)
                time.sleep(3)

                body = page.locator("body").inner_text(timeout=10_000).lower()
                nav.close()

            agotado_kw = ["agotado", "sold out", "no tickets available"]
            agotado = any(k in body for k in agotado_kw)

            if not agotado:
                estado = "disponible"
                if (
                    self._ultimo_estado_scraping is not None
                    and self._ultimo_estado_scraping != estado
                ):
                    self._ultimo_estado_scraping = estado
                    return (True, True)

                if self._ultimo_estado_scraping is None:
                    self._ultimo_estado_scraping = estado
                    logger.info("[%s] Estado inicial scraping: disponible", self.nombre)
                return (True, False)

            if self._ultimo_estado_scraping is None:
                self._ultimo_estado_scraping = "agotado"
                logger.info("[%s] Estado inicial scraping: agotado", self.nombre)
            elif self._ultimo_estado_scraping != "agotado":
                self._ultimo_estado_scraping = "agotado"

            return (True, False)

        except Exception as e:
            logger.error("[%s] Error scraping: %s", self.nombre, e)
            return (False, False)

    def alertar(self, mensaje: str):
        if self.telegram_chat_id:
            enviar_alerta(mensaje, chat_id=self.telegram_chat_id)
        if self.whatsapp_chat_id:
            enviar_reporte_wa(mensaje, chat_id=self.whatsapp_chat_id)


def cargar_clientes() -> list[MonitorCliente]:
    try:
        with open(RUTA_CLIENTES, encoding="utf-8") as f:
            raw = json.load(f)
        return [MonitorCliente(c) for c in raw if c.get("habilitado", True)]
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error("Error cargando %s: %s", RUTA_CLIENTES, e)
        return []


def ejecutar_ciclo(clientes: list[MonitorCliente]):
    for cli in clientes:
        logger.info("--- [%s] ---", cli.nombre)

        if cli.api_disponible and cli._contador_fallos_api < config.MAX_API_FAILURES:
            exito, hay_boletas = cli.verificar_api()
            if exito:
                cli._contador_fallos_api = 0
                if hay_boletas:
                    msg = (
                        f"ALERTA {cli.nombre}! Boletas disponibles! "
                        f"Revisa: {cli.url_scraping or cli.evento_id}"
                    )
                    cli.alertar(msg)
            else:
                cli._contador_fallos_api += 1
                logger.warning(
                    "[%s] Fallo API (%s/%s)",
                    cli.nombre,
                    cli._contador_fallos_api,
                    config.MAX_API_FAILURES,
                )
            continue

        exito_s, hay_boletas_s = cli.verificar_scraping()
        if exito_s and hay_boletas_s:
            msg = (
                f"ALERTA SCRAPER {cli.nombre}! Boletas posibles! "
                f"Entra ya: {cli.url_scraping}"
            )
            cli.alertar(msg)
        elif not exito_s:
            logger.error("[%s] Fallaron ambos sistemas", cli.nombre)
            cli.alertar(
                f"ERROR {cli.nombre}: Ambos sistemas de monitoreo fallaron"
            )
