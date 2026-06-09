"""
Módulo de configuración centralizada para TicketmasterBot.

Carga variables de entorno desde un archivo .env usando python-dotenv
y define constantes estáticas para el monitoreo híbrido.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# === Variables de entorno (cargadas desde .env) ===
TELEGRAM_TOKEN: str | None = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID: str | None = os.getenv("TELEGRAM_CHAT_ID")
TICKETMASTER_API_KEY: str | None = os.getenv("TICKETMASTER_API_KEY")
TICKETMASTER_EVENT_ID: str | None = os.getenv("TICKETMASTER_EVENT_ID")

# === OpenWA (WhatsApp) ===
OPENWA_URL: str = os.getenv("OPENWA_URL", "http://localhost:2785/api")
OPENWA_API_KEY: str | None = os.getenv("OPENWA_API_KEY")
OPENWA_CHAT_ID: str | None = os.getenv("OPENWA_CHAT_ID")
OPENWA_SESSION: str = os.getenv("OPENWA_SESSION", "ticketmaster-bot")

# === Flags de disponibilidad ===
API_DISPONIBLE: bool = bool(TICKETMASTER_API_KEY and TICKETMASTER_EVENT_ID)
OPENWA_DISPONIBLE: bool = bool(OPENWA_API_KEY and OPENWA_CHAT_ID)

# === Constantes estáticas de configuración ===
API_BASE_URL: str = "https://app.ticketmaster.com/discovery/v2/events/"
EVENT_URL_SCRAPING: str = "https://www.ticketmaster.co/event/bts-world-tour-2026"
API_DELAY: int = 20
MAX_API_FAILURES: int = 3
TELEGRAM_RETRIES: int = 3
OPENWA_RETRIES: int = 3
