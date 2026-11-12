import os

import requests
import yfinance as yf

# --- Configuración (cámbiala a tu gusto) ---
 # símbolos de Yahoo Finance
PERIODO = "1y"                          # historial a descargar
TICKERS = ["AAPL", "MSFT", "BTC-USD", "TSLA", "NVDA", "AMZN", "GOOGL", "META"]
SMA_RAPIDA = 3
SMA_LENTA = 8


def obtener_datos(ticker: str):
    """Descarga precios diarios de cierre."""
    df = yf.download(
        ticker, period=PERIODO, interval="1d",
        auto_adjust=True, progress=False,
    )
    # Algunas versiones de yfinance devuelven columnas con varios niveles
    if df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)
    return df


def detectar_cruce(df):
    """Devuelve 'ALCISTA', 'BAJISTA' o None según la última vela."""
    df = df.copy()
    df["rapida"] = df["Close"].rolling(SMA_RAPIDA).mean()
    df["lenta"] = df["Close"].rolling(SMA_LENTA).mean()

    ayer, hoy = df.iloc[-2], df.iloc[-1]

    if ayer["rapida"] <= ayer["lenta"] and hoy["rapida"] > hoy["lenta"]:
        return "ALCISTA"
    if ayer["rapida"] >= ayer["lenta"] and hoy["rapida"] < hoy["lenta"]:
        return "BAJISTA"
    return None


def enviar_alerta(mensaje: str):
    """Imprime la alerta y, si está configurado, la manda por Telegram."""
    print(mensaje)

    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": mensaje},
            timeout=10,
        )


def main():
    for ticker in TICKERS:
        try:
            df = obtener_datos(ticker)
            if len(df) < SMA_LENTA + 2:
                print(f"{ticker}: datos insuficientes")
                continue

            cruce = detectar_cruce(df)
            precio = float(df["Close"].iloc[-1])

            if cruce:
                enviar_alerta(
                    f"🔔 {ticker}: cruce {cruce} "
                    f"(SMA{SMA_RAPIDA} vs SMA{SMA_LENTA}), precio {precio:.2f}"
                )
            else:
                print(f"{ticker}: sin cruce (precio {precio:.2f})")
        except Exception as e:
            print(f"{ticker}: error -> {e}")


if __name__ == "__main__":
    main()