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
    if t != "^BVSP" and not t.endswith(".SA") and not t.endswith("34"):
        t += ".SA"
    return t


@st.cache_data
def baixar_dados(tickers, inicio, fim):
    df = yf.download(tickers, start=inicio, end=fim, progress=False)

    if df.empty:
        raise ValueError("Nenhum dado retornado.")

    if isinstance(df.columns, pd.MultiIndex):
        niveis = df.columns.get_level_values(0)

        if "Adj Close" in niveis:
            df = df["Adj Close"]
        elif "Close" in niveis:
            df = df["Close"]
        else:
            raise KeyError("Sem coluna de preço válida.")

    else:
        if "Adj Close" in df.columns:
            df = df[["Adj Close"]]
        elif "Close" in df.columns:
            df = df[["Close"]]
        else:
            raise KeyError("Sem coluna de preço válida.")

        df.columns = [tickers[0]]

    return df.dropna(how="all")


def calcular_carteira(dados, aporte_mensal, investimento_inicial, modo):
    cotas = pd.DataFrame(0, index=dados.index, columns=dados.columns)

    # =========================
    # INVESTIMENTO INICIAL
    # =========================
    if modo in ["Apenas inicial", "Inicial + mensal"]:
        primeira_data = dados.index[0]

        for col in dados.columns:
            cotas.loc[primeira_data, col] += (
                investimento_inicial / len(dados.columns)
            ) / dados.loc[primeira_data, col]

    # =========================
    # APORTES MENSAIS
    # =========================
    if modo in ["Aporte mensal", "Inicial + mensal"]:
        datas_aporte = dados.resample("M").first().index

        for data in datas_aporte:
            if data in dados.index:
                for col in dados.columns:
                    cotas.loc[data, col] += (
                        aporte_mensal / len(dados.columns)
                    ) / dados.loc[data, col]

        n_aportes = len(datas_aporte)
    else:
        n_aportes = 0

    cotas_acum = cotas.cumsum()
    carteira = (cotas_acum * dados).sum(axis=1)

    return carteira, n_aportes


def calcular_metricas(retornos):
    if len(retornos) < 2:
        return 0, 0, 0

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

modo = st.sidebar.selectbox(
    "Tipo de investimento",
    ["Apenas inicial", "Aporte mensal", "Inicial + mensal"]
)

investimento_inicial = st.sidebar.number_input(
    "Investimento inicial (R$)",
    value=10000.0
)

aporte_mensal = st.sidebar.number_input(
    "Aporte mensal (R$)",
    value=1000.0
)

csv_file = st.sidebar.file_uploader("Upload carteira CSV", type=["csv"])

# =========================
# TRATAR ATIVOS
# =========================

try:
    if csv_file:
        df_csv = pd.read_csv(csv_file)
        ativos = [tratar_ticker(x) for x in df_csv["ticker"]]
    else:
        ativos = [tratar_ticker(x) for x in ativos_input.split(",")]

    ativos = list(set(ativos))

    if "^BVSP" not in ativos:
        ativos.append("^BVSP")

except Exception:
    st.error("Erro ao ler ativos.")
    st.stop()

if inicio >= fim:
    st.error("Data inicial deve ser menor que final.")
    st.stop()

# =========================
# DADOS
# =========================

try:
    dados = baixar_dados(ativos, inicio, fim)
except Exception as e:
    st.error(f"Erro ao baixar dados: {e}")
    st.stop()

if dados.empty:
    st.error("Sem dados disponíveis.")
    st.stop()

# separa IBOV
if "^BVSP" in dados.columns:
    ibov = dados["^BVSP"]
    dados = dados.drop(columns="^BVSP")
    usar_ibov = True
else:
    usar_ibov = False
    st.warning("IBOV não disponível.")

if dados.empty:
    st.error("Nenhum ativo válido.")
    st.stop()

# =========================
# CARTEIRA
# =========================

carteira, n_aportes = calcular_carteira(
    dados,
    aporte_mensal,
    investimento_inicial,
    modo
)

# =========================
# MÉTRICAS
# =========================

retornos = carteira.pct_change().dropna()
ret_medio, vol, sharpe = calcular_metricas(retornos)

investido = 0

if modo in ["Apenas inicial", "Inicial + mensal"]:
    investido += investimento_inicial

if modo in ["Aporte mensal", "Inicial + mensal"]:
    investido += aporte_mensal * n_aportes

valor_final = carteira.iloc[-1]
lucro = valor_final - investido
ir = lucro * 0.15 if lucro > 0 else 0

# =========================
# UI
# =========================

st.title("🚀 Simulador Profissional de Carteira")

c1, c2, c3, c4 = st.columns(4)
c1.metric("💰 Investido", f"R$ {investido:,.2f}")
c2.metric("📈 Valor Final", f"R$ {valor_final:,.2f}")
c3.metric("💸 Lucro", f"R$ {lucro:,.2f}")
c4.metric("🧾 IR (15%)", f"R$ {ir:,.2f}")

c5, c6 = st.columns(2)
c5.metric("📊 Retorno Anual", f"{ret_medio*100:.2f}%")
c6.metric("📉 Volatilidade", f"{vol*100:.2f}%")

st.metric("⚡ Sharpe Ratio", f"{sharpe:.2f}")

# =========================
# GRÁFICO
# =========================

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=carteira.index,
    y=carteira,
    name="Carteira"
))

if usar_ibov:
    ibov_norm = (ibov / ibov.iloc[0]) * carteira.iloc[0]

    fig.add_trace(go.Scatter(
        x=ibov.index,
        y=ibov_norm,
        name="IBOV"
    ))

fig.update_layout(template="plotly_dark", title="Performance")

st.plotly_chart(fig, use_container_width=True)

# =========================
# DEBUG
# =========================

with st.expander("🔍 Debug"):
    st.write("Ativos:", ativos)
    st.write("Colunas:", dados.columns)

# =========================
# TABELA
# =========================

with st.expander("📄 Dados históricos"):
    st.dataframe(dados.tail(50))
