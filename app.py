import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Simulador B3 PRO MAX", layout="wide")

# =========================
# FUNÇÕES
# =========================

def tratar_ticker(t):
    t = t.upper().strip()
    if not t.endswith(".SA") and t != "^BVSP":
        t += ".SA"
    return t


@st.cache_data
def baixar_dados(tickers, inicio, fim):
    dados = yf.download(tickers, start=inicio, end=fim, progress=False)["Adj Close"]
    return dados.dropna(how="all")


def calcular_carteira(dados, aportes):
    cotas = pd.DataFrame(index=dados.index, columns=dados.columns)

    for col in dados.columns:
        cotas[col] = aportes / dados[col]

    cotas_acum = cotas.cumsum()
    carteira = (cotas_acum * dados).sum(axis=1)

    return carteira


def calcular_metricas(retornos):
    retorno_medio = retornos.mean() * 252
    vol = retornos.std() * np.sqrt(252)
    sharpe = retorno_medio / vol if vol != 0 else 0
    return retorno_medio, vol, sharpe


# =========================
# SIDEBAR
# =========================

st.sidebar.header("⚙️ Configurações")

ativos_input = st.sidebar.text_input(
    "Ativos (separados por vírgula)",
    "PETR4,VALE3"
)

inicio = st.sidebar.date_input("Data início", datetime(2023, 1, 1))
fim = st.sidebar.date_input("Data fim", datetime.today())

aporte_mensal = st.sidebar.number_input("Aporte mensal (R$)", value=1000.0)
usar_csv = st.sidebar.file_uploader("Upload carteira (CSV)", type=["csv"])

# =========================
# TRATAR ATIVOS
# =========================

if usar_csv:
    df_csv = pd.read_csv(usar_csv)
    ativos = [tratar_ticker(x) for x in df_csv["ticker"]]
else:
    ativos = [tratar_ticker(x) for x in ativos_input.split(",")]

ativos.append("^BVSP")  # benchmark

# =========================
# DADOS
# =========================

dados = baixar_dados(ativos, inicio, fim)

if dados.empty:
    st.error("Sem dados.")
    st.stop()

# separa IBOV
ibov = dados["^BVSP"]
dados = dados.drop(columns="^BVSP")

# =========================
# DCA
# =========================

datas_aporte = dados.resample("M").first().index
aportes = pd.Series(aporte_mensal, index=datas_aporte)

carteira = calcular_carteira(dados, aporte_mensal)

# =========================
# RETORNOS
# =========================

retornos = carteira.pct_change().dropna()
ret_ibov = ibov.pct_change().dropna()

ret_medio, vol, sharpe = calcular_metricas(retornos)

# =========================
# IR (simplificado 15%)
# =========================

lucro = carteira.iloc[-1] - (aporte_mensal * len(datas_aporte))
ir = lucro * 0.15 if lucro > 0 else 0

# =========================
# UI
# =========================

st.title("🚀 Simulador PRO de Carteira")

c1, c2, c3, c4 = st.columns(4)
c1.metric("💰 Valor Final", f"R$ {carteira.iloc[-1]:,.2f}")
c2.metric("📈 Lucro", f"R$ {lucro:,.2f}")
c3.metric("🧾 IR (15%)", f"R$ {ir:,.2f}")
c4.metric("⚡ Sharpe", f"{sharpe:.2f}")

c5, c6 = st.columns(2)
c5.metric("📊 Retorno Anual", f"{ret_medio*100:.2f}%")
c6.metric("📉 Volatilidade", f"{vol*100:.2f}%")

# =========================
# GRÁFICO
# =========================

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=carteira.index,
    y=carteira,
    name="Carteira"
))

fig.add_trace(go.Scatter(
    x=ibov.index,
    y=(ibov / ibov.iloc[0]) * carteira.iloc[0],
    name="IBOV (normalizado)"
))

fig.update_layout(template="plotly_dark")

st.plotly_chart(fig, use_container_width=True)

# =========================
# TABELA
# =========================

with st.expander("📄 Dados"):
    st.dataframe(dados.tail(50))
