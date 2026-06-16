import json
import logging
import random
import time

import requests

import config
from notificador import enviar_alerta
from reporte_wa import enviar_reporte_wa

logger = logging.getLogger(__name__)

RUTA_CLIENTES = "clientes.json"

PALABRAS_AGOTADO = [
    "agotado", "sold out", "no tickets", "entradas agotadas",
    "no hay entradas", "no disponible", "evento finalizado",
]
PALABRAS_DISPONIBLE = [
    "comprar", "get tickets", "buy tickets", "boletas",
    "ver boletas", "encuentra tus boletas", "elige tu",
    "precios", "mapa", "ubicacion",
]
SELECTORES_DISPONIBLE = [
    "button:has-text('Comprar')",
    "button:has-text('Get Tickets')",
    "button:has-text('Buy')",
    "button:has-text('Ver boletas')",
    "button:has-text('Boletas')",
    "button:has-text('Continuar')",
    "[data-testid='buy-tickets-button']",
    "[data-automation='buy-tickets-button']",
    "a:has-text('Comprar')",
    "a:has-text('Get Tickets')",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

COOLDOWN_ERROR_SEGUNDOS = 300


class MonitorCliente:
    def __init__(self, cfg: dict):
        self.nombre = cfg["nombre"]
        self.evento_id = cfg.get("evento_id", "") or ""
        self.url_scraping = cfg.get("url_scraping", "")
        self.telegram_chat_id = cfg.get("telegram_chat_id") or None
        self.whatsapp_chat_id = cfg.get("whatsapp_chat_id") or None
        self.habilitado = cfg.get("habilitado", True)
        self.alertar_inicial = cfg.get("alertar_inicial", False)

        self.api_disponible = bool(config.TICKETMASTER_API_KEY and self.evento_id)
        self._ultimo_estado_api: str | None = None
        self._ultimo_estado_scraping: str | None = None
        self._contador_fallos_api = 0
        self._ultimo_error_alertado = 0.0

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
                    logger.info("[%s] Estado inicial API: %s", self.nombre, estado)
                    if estado == "onsale" and self.alertar_inicial:
                        return (True, True)
                return (True, False)

            if r.status_code in (429, 401, 403):
                return (False, False)
            return (False, False)

        except requests.exceptions.RequestException:
            return (False, False)

    def _aceptar_cookies(self, page):
        selectores_cookies = [
            "button:has-text('Aceptar')",
            "button:has-text('Accept')",
            "button:has-text('Aceptar todo')",
            "button:has-text('Accept all')",
            "#onetrust-accept-btn-handler",
            ".cookie-accept",
            "[aria-label='Accept cookies']",
        ]
        for sel in selectores_cookies:
            try:
                btn = page.locator(sel)
                if btn.count() > 0 and btn.first.is_visible(timeout=2000):
                    btn.first.click()
                    page.wait_for_timeout(1000)
                    logger.info("[%s] Cookies aceptadas via '%s'", self.nombre, sel)
                    return
            except Exception:
                continue

    def _analizar_disponibilidad_scraping(self, page) -> tuple[bool, str]:
        self._aceptar_cookies(page)
        page.wait_for_timeout(random.uniform(3000, 5000))

        body_text = page.locator("body").inner_text(timeout=10_000).lower()

        for kw in PALABRAS_AGOTADO:
            if kw in body_text:
                logger.info("[%s] Texto agotado detectado: '%s'", self.nombre, kw)
                return (False, f"texto_agotado:'{kw}'")

        for selector in SELECTORES_DISPONIBLE:
            try:
                el = page.locator(selector)
                if el.count() > 0 and el.first.is_visible(timeout=2000):
                    logger.info("[%s] Selector compra visible: '%s'", self.nombre, selector)
                    return (True, f"selector:'{selector}'")
            except Exception:
                continue

        for kw in PALABRAS_DISPONIBLE:
            if kw in body_text:
                logger.info("[%s] Texto disponible detectado: '%s'", self.nombre, kw)
                return (True, f"texto_disponible:'{kw}'")

        logger.info("[%s] Sin indicadores positivos en pagina", self.nombre)
        return (False, "sin_indicadores_positivos")

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
                    user_agent=random.choice(USER_AGENTS),
                    viewport={"width": 1920, "height": 1080},
                )
                page = ctx.new_page()
                logger.info("[%s] Scraping %s ...", self.nombre, self.url_scraping)

                try:
                    page.goto(self.url_scraping, timeout=25_000, wait_until="load")
                except Exception:
                    logger.warning("[%s] Load timeout, fallback a domcontentloaded", self.nombre)
                    page.goto(self.url_scraping, timeout=15_000, wait_until="domcontentloaded")

                disponible, razon = self._analizar_disponibilidad_scraping(page)
                nav.close()

            estado = "disponible" if disponible else "agotado"

            if self._ultimo_estado_scraping is not None and self._ultimo_estado_scraping != estado:
                if disponible:
                    logger.info(
                        "[%s] Cambio detectado! agotado -> disponible (por %s)",
                        self.nombre, razon,
                    )
                self._ultimo_estado_scraping = estado
                return (True, disponible)

            if self._ultimo_estado_scraping is None:
                self._ultimo_estado_scraping = estado
                logger.info(
                    "[%s] Estado inicial scraping: %s (por %s)",
                    self.nombre, estado, razon,
                )
                if disponible and self.alertar_inicial:
                    return (True, True)

            return (True, False)

        except Exception as e:
            logger.error("[%s] Error scraping: %s", self.nombre, e)
            return (False, False)

    def alertar(self, mensaje: str):
        if self.telegram_chat_id:
            enviar_alerta(mensaje, chat_id=self.telegram_chat_id)
        if self.whatsapp_chat_id:
            enviar_reporte_wa(mensaje, chat_id=self.whatsapp_chat_id)

    def alertar_error_con_cooldown(self, mensaje: str):
        ahora = time.time()
        if ahora - self._ultimo_error_alertado >= COOLDOWN_ERROR_SEGUNDOS:
            self._ultimo_error_alertado = ahora
            self.alertar(mensaje)


def cargar_clientes() -> list[MonitorCliente]:
    try:
        with open(RUTA_CLIENTES, encoding="utf-8") as f:
            raw = json.load(f)
        vistos = set()
        resultado = []
        for c in raw:
            if not c.get("habilitado", True):
                continue
            nombre = c["nombre"]
            if nombre in vistos:
                logger.warning("Cliente duplicado ignorado: '%s'", nombre)
                continue
            vistos.add(nombre)
            resultado.append(MonitorCliente(c))
        return resultado
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
            logger.error("[%s] Error al consultar scraping", cli.nombre)
            cli.alertar_error_con_cooldown(
                f"ERROR {cli.nombre}: No se pudo consultar el evento "
                f"(timeout o bloqueo). El monitoreo continua."
            )
