# TicketmasterBot

Bot híbrido de monitoreo de eventos de Ticketmaster que detecta disponibilidad de boletas y envía alertas por Telegram.

## Arquitectura

```
                 ┌─────────────────┐
                 │   main.py       │ ← Orquestador (ciclo infinito)
                 └──────┬──────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
  ┌──────────────┐ ┌──────────┐ ┌──────────┐
  │ monitor_api  │ │ monitor_ │ │notificador│
  │ .py          │ │scraping  │ │ .py       │
  │ (API oficial)│ │ .py      │ │(Telegram) │
  └──────────────┘ │(Playwright│ └──────────┘
                   │ fallback) │
                   └──────────┘
```

### Componentes

| Módulo | Función |
|---|---|
| `main.py` | Orquestador con failover automático API → scraping |
| `config.py` | Configuración centralizada desde `.env` |
| `monitor_api.py` | Consulta Ticketmaster Discovery v2 API |
| `monitor_scraping.py` | Web scraping con Playwright (fallback) |
| `notificador.py` | Alertas a Telegram con retry y backoff exponencial |
| `buscar_evento.py` | Busca eventos en la API y obtiene su ID |

### Flujo

1. Intenta usar la **API oficial** de Ticketmaster (`monitor_api.py`)
2. Si la API falla 3 veces seguidas o no hay API key configurada, hace **failover a scraping** con Playwright
3. Detecta cambios de estado (`onsale`, `agotado`) y envía alerta por Telegram
4. Ciclo cada 20 segundos (configurable)

## Requisitos

- Python 3.10+
- Playwright (instala Chromium: `playwright install chromium`)

## Instalación

```bash
git clone https://github.com/Mate0521/TickermasterBoot.git
cd TickermasterBoot
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# Edita .env con tus credenciales
python main.py
```

## Configuración

Edita `.env` (ver `.env.example`):

| Variable | Obligatorio | Descripción |
|---|---|---|
| `TELEGRAM_TOKEN` | Sí | Token de @BotFather |
| `TELEGRAM_CHAT_ID` | Sí | Chat ID de Telegram |
| `TICKETMASTER_API_KEY` | No | API key de Developer Portal |
| `TICKETMASTER_EVENT_ID` | No | ID del evento a monitorear |

Si no configuras API key, el bot funciona **solo con scraping**.

## Despliegue en Oracle Cloud

```bash
curl -fsSL https://raw.githubusercontent.com/Mate0521/TickermasterBoot/main/deploy.sh | bash
# Editar credenciales: nano ~/ticketmaster/.env
# Iniciar: sudo systemctl start ticketmasterbot
```

## Uso: Buscar eventos

```bash
python buscar_evento.py              # Busca "BTS" global
python buscar_evento.py "Bad Bunny"  # Busca otro artista
python buscar_evento.py "BTS" CO     # Filtra por país
```

## Licencia

MIT
