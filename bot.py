"""
Bot interactivo de Telegram.

Le mandas un número o un símbolo y te responde con el precio,
las medias móviles y la tendencia. Solo responde a tu chat.

Uso (con el entorno virtual activo):
    python bot.py

Detenerlo: Ctrl + C
Requiere las variables TELEGRAM_TOKEN y TELEGRAM_CHAT_ID.
"""

import os
import re
import time

import requests

from alerta_cruce import (
    SMA_LENTA,
    SMA_RAPIDA,
    TICKERS,
    detectar_cruce,
    obtener_datos,
)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
URL = f"https://api.telegram.org/bot{TOKEN}"


def enviar(texto: str):
    requests.post(
        f"{URL}/sendMessage",
        data={"chat_id": CHAT_ID, "text": texto},
        timeout=15,
    )


def obtener_mensajes(offset):
    """Espera hasta 30 s por mensajes nuevos (long polling)."""
    r = requests.get(
        f"{URL}/getUpdates",
        params={"timeout": 30, "offset": offset},
        timeout=40,
    )
    return r.json().get("result", [])


def resumen(ticker: str) -> str:
    df = obtener_datos(ticker)
    if df.empty or len(df) < SMA_LENTA + 2:
        return f"{ticker}: no encontré datos suficientes."

    df = df.copy()
    df["rapida"] = df["Close"].rolling(SMA_RAPIDA).mean()
    df["lenta"] = df["Close"].rolling(SMA_LENTA).mean()

    hoy = df.iloc[-1]
    precio = float(hoy["Close"])
    cambio = (precio / float(df["Close"].iloc[-2]) - 1) * 100
    rapida = float(hoy["rapida"])
    lenta = float(hoy["lenta"])

    if rapida > lenta:
        tendencia = "ALCISTA (rápida sobre lenta)"
    else:
        tendencia = "BAJISTA (rápida bajo lenta)"

    cruce = detectar_cruce(df)
    if cruce:
        linea_cruce = f"🔔 Cruce {cruce} en la última vela"
    else:
        linea_cruce = "Sin cruce en la última vela"

    return (
        f"📊 {ticker}\n"
        f"Precio: {precio:.2f} ({cambio:+.2f}% vs día anterior)\n"
        f"SMA{SMA_RAPIDA}: {rapida:.2f}\n"
        f"SMA{SMA_LENTA}: {lenta:.2f}\n"
        f"Tendencia: {tendencia}\n"
        f"{linea_cruce}"
    )


def menu() -> str:
    lineas = ["Envíame un número o un símbolo:", "0 - resumen de todos"]
    for i, t in enumerate(TICKERS, start=1):
        lineas.append(f"{i} - {t}")
    lineas.append("O escribe cualquier símbolo de Yahoo Finance (ej. NVDA, ETH-USD)")
    return "\n".join(lineas)


def responder(texto: str) -> str:
    texto = texto.strip().upper()

    if texto in ("/START", "/AYUDA", "/MENU", "AYUDA", "MENU"):
        return menu()

    if texto.isdigit():
        n = int(texto)
        if n == 0:
            return "\n\n".join(resumen(t) for t in TICKERS)
        if 1 <= n <= len(TICKERS):
            return resumen(TICKERS[n - 1])
        return "Ese número no está en la lista.\n\n" + menu()

    if re.fullmatch(r"[A-Z0-9.\-=^]{1,12}", texto):
        return resumen(texto)

    return menu()


def main():
    if not TOKEN or not CHAT_ID:
        print("Faltan las variables TELEGRAM_TOKEN y/o TELEGRAM_CHAT_ID.")
        return

    # Ignora los mensajes viejos que quedaron pendientes
    pendientes = requests.get(
        f"{URL}/getUpdates", params={"offset": -1}, timeout=15
    ).json().get("result", [])
    offset = pendientes[-1]["update_id"] + 1 if pendientes else None

    print("Bot activo. Presiona Ctrl + C para detenerlo.")
    enviar("Bot activo ✅ Escribe 'menu' para ver las opciones.")

    try:
        while True:
            try:
                for upd in obtener_mensajes(offset):
                    offset = upd["update_id"] + 1
                    msg = upd.get("message", {})

                    # Solo responde a tu chat
                    if str(msg.get("chat", {}).get("id")) != str(CHAT_ID):
                        continue

                    texto = msg.get("text")
                    if not texto:
                        continue

                    try:
                        enviar(responder(texto))
                    except Exception as e:
                        enviar(f"Ocurrió un error: {e}")
            except requests.RequestException:
                time.sleep(5)
    except KeyboardInterrupt:
        print("Bot detenido.")


if __name__ == "__main__":
    main()
