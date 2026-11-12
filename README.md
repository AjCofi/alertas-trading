# Alertas de trading con Python

Script que descarga precios de mercado y envía una alerta cuando
una media móvil rápida cruza a una lenta (cruce alcista o bajista).

## Cómo usarlo

1. Crear y activar un entorno virtual
2. `pip install -r requirements.txt`
3. `python alerta_cruce.py`

## Tecnologías

Python, pandas, yfinance, API de Telegram (opcional)

## Aviso

Proyecto educativo. No es una recomendación de inversión.

## Bot interactivo

`bot.py` responde en Telegram con el precio, las medias móviles y la
tendencia de cada símbolo. Envía un número del menú o un símbolo
(ej. NVDA) y recibes el resumen.

Uso: `python bot.py` (requiere TELEGRAM_TOKEN y TELEGRAM_CHAT_ID).