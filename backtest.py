"""
Backtest del cruce de medias móviles.

Regla: estar comprado cuando la media rápida está por encima de la lenta,
y fuera del mercado (en efectivo) cuando está por debajo.
La señal de hoy se ejecuta MAÑANA, para no usar información del futuro.

Compara la estrategia contra simplemente comprar y mantener.

Uso (con el entorno virtual activo):
    python backtest.py            # usa los símbolos de TICKERS
    python backtest.py NVDA TSLA  # o los que le indiques

Opcional, para guardar gráficas:  pip install matplotlib
"""

import os
import sys

import yfinance as yf

from alerta_cruce import SMA_LENTA, SMA_RAPIDA, TICKERS

# --- Configuración ---
PERIODO = "10y"     # años de historial
COMISION = 0.001    # 0.1% por cada compra o venta


def descargar(ticker: str):
    df = yf.download(
        ticker, period=PERIODO, interval="1d",
        auto_adjust=True, progress=False,
    )
    if df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)
    return df.dropna()


def backtest(df):
    """Calcula posición, retornos de la estrategia y operaciones."""
    df = df.copy()
    df["ret"] = df["Close"].pct_change().fillna(0)
    df["rapida"] = df["Close"].rolling(SMA_RAPIDA).mean()
    df["lenta"] = df["Close"].rolling(SMA_LENTA).mean()

    senal = (df["rapida"] > df["lenta"]).astype(int)
    # shift(1): la señal de hoy se opera mañana
    df["posicion"] = senal.shift(1).fillna(0).astype(int)

    cambios = df["posicion"].diff().abs().fillna(0)
    df["ret_est"] = df["posicion"] * df["ret"] - cambios * COMISION

    # Retorno de cada operación (sin comisiones)
    entradas = df["posicion"].diff() == 1
    df["trade_id"] = entradas.cumsum() * df["posicion"]
    en_mercado = df[df["trade_id"] > 0]
    trades = (1 + en_mercado["ret"]).groupby(en_mercado["trade_id"]).prod() - 1

    return df, trades


def metricas(ret, anios: float):
    equity = (1 + ret).cumprod()
    total = equity.iloc[-1] - 1
    cagr = equity.iloc[-1] ** (1 / anios) - 1
    caida = (equity / equity.cummax() - 1).min()
    por_anio = len(ret) / anios
    sharpe = ret.mean() / ret.std() * por_anio ** 0.5 if ret.std() > 0 else 0.0
    return {"total": total, "cagr": cagr, "caida": caida, "sharpe": sharpe}, equity


def graficar(ticker, eq_est, eq_bh):
    """Guarda una gráfica en la carpeta resultados/ (si hay matplotlib)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    os.makedirs("resultados", exist_ok=True)
    plt.figure(figsize=(9, 4.5))
    plt.plot(eq_est.index, eq_est, label=f"Cruce SMA{SMA_RAPIDA}/{SMA_LENTA}")
    plt.plot(eq_bh.index, eq_bh, label="Comprar y mantener")
    plt.title(f"{ticker}: crecimiento de $1")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"resultados/{ticker}.png", dpi=120)
    plt.close()
    return True


def pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def analizar(ticker: str):
    df = descargar(ticker)
    if len(df) < SMA_LENTA + 100:
        print(f"{ticker}: datos insuficientes\n")
        return None

    df, trades = backtest(df)
    anios = (df.index[-1] - df.index[0]).days / 365.25

    m_est, eq_est = metricas(df["ret_est"], anios)
    m_bh, eq_bh = metricas(df["ret"], anios)

    n = len(trades)
    ganadoras = int((trades > 0).sum())
    tasa = ganadoras / n * 100 if n else 0.0
    tiempo = df["posicion"].mean() * 100

    print(f"=== {ticker} ({anios:.1f} años) ===")
    print(f"{'':22}{'Estrategia':>12}{'Comprar y mantener':>22}")
    print(f"{'Retorno total':22}{pct(m_est['total']):>12}{pct(m_bh['total']):>22}")
    print(f"{'Retorno anual':22}{pct(m_est['cagr']):>12}{pct(m_bh['cagr']):>22}")
    print(f"{'Caída máxima':22}{pct(m_est['caida']):>12}{pct(m_bh['caida']):>22}")
    print(f"{'Sharpe':22}{m_est['sharpe']:>12.2f}{m_bh['sharpe']:>22.2f}")
    print(f"Operaciones: {n} | ganadoras: {tasa:.0f}% | "
          f"tiempo en el mercado: {tiempo:.0f}%")

    if graficar(ticker, eq_est, eq_bh):
        print(f"Gráfica guardada en resultados/{ticker}.png")
    print()

    return m_est, m_bh


def main():
    tickers = [t.upper() for t in sys.argv[1:]] or TICKERS
    print(f"Backtest: cruce SMA{SMA_RAPIDA}/SMA{SMA_LENTA}, "
          f"comisión {COMISION * 100:.1f}% por operación\n")

    resultados = []
    for t in tickers:
        try:
            r = analizar(t)
            if r:
                resultados.append(r)
        except Exception as e:
            print(f"{t}: error -> {e}\n")

    if resultados:
        total = len(resultados)
        gana_ret = sum(e["total"] > b["total"] for e, b in resultados)
        menor_caida = sum(e["caida"] > b["caida"] for e, b in resultados)
        print("=== RESUMEN ===")
        print(f"Mejor retorno que comprar y mantener: {gana_ret} de {total}")
        print(f"Menor caída máxima que comprar y mantener: {menor_caida} de {total}")
        print("\nRecuerda: el pasado no garantiza el futuro, y este backtest no "
              "incluye impuestos ni deslizamiento de precios.")


if __name__ == "__main__":
    main()
