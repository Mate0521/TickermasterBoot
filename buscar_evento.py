"""
Script de prueba para buscar eventos en Ticketmaster Discovery API
y obtener el eventId real necesario para el monitoreo.

Uso:
    python buscar_evento.py                          # Busca "BTS" global
    python buscar_evento.py "Bad Bunny"              # Busca otro artista
    python buscar_evento.py "BTS" CO                 # Filtra por país (CO, US, ES, etc.)
"""

import sys

import requests
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("TICKETMASTER_API_KEY")
URL = "https://app.ticketmaster.com/discovery/v2/events.json"


def buscar_eventos(keyword: str, pais: str = ""):
    if not API_KEY:
        print("ERROR: Define TICKETMASTER_API_KEY en .env primero")
        return

    params = {"apikey": API_KEY, "keyword": keyword, "size": 20}
    if pais:
        params["countryCode"] = pais

    ubicacion = f" en '{pais}'" if pais else " (global)"
    print(f"Buscando eventos con: '{keyword}'{ubicacion}...\n")

    resp = requests.get(URL, params=params, timeout=15)

    if resp.status_code != 200:
        print(f"Error HTTP {resp.status_code}: {resp.text[:200]}")
        return

    data = resp.json()
    page = data.get("page", {})
    total = page.get("totalElements", 0)
    print(f"Total de eventos encontrados: {total}\n")

    eventos = data.get("_embedded", {}).get("events", [])

    if not eventos:
        print("No se encontraron eventos.")
        return

    for ev in eventos:
        eid = ev.get("id", "?")
        nombre = ev.get("name", "?")
        fecha = ev.get("dates", {}).get("start", {}).get("localDate", "?")
        estado = ev.get("dates", {}).get("status", {}).get("code", "?")
        url = ev.get("url", "?")
        venue = ev.get("_embedded", {}).get("venues", [{}])[0]
        ciudad = venue.get("city", {}).get("name", "?")
        pais_ev = venue.get("country", {}).get("countryCode", "?")

        print(f"ID:      {eid}")
        print(f"Evento:  {nombre}")
        print(f"Fecha:   {fecha}  |  Estado: {estado}")
        print(f"Lugar:   {ciudad}, {pais_ev}")
        print(f"URL:     {url}")
        print("-" * 60)


if __name__ == "__main__":
    keyword = sys.argv[1] if len(sys.argv) > 1 else "BTS"
    pais = sys.argv[2] if len(sys.argv) > 2 else ""
    buscar_eventos(keyword, pais)
