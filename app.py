import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="Simulador B3 Pro", layout="wide")

# =========================
# FUNÇÕES
# =========================

def tratar_ticker(nome: str) -> str:
    nome = nome.upper().strip()

    de_para = {
        "ITAU": "ITUB4", "ITAÚ": "ITUB4", "SANTANDER": "SANB11",
        "INTER": "INTR", "BANCO INTER": "INTR", "BRADESCO": "BBDC4",
        "BANCO DO BRASIL": "BBAS3", "BB": "BBAS3", "NUBANK": "ROXO34",
        "BTG": "BPAC11", "XP": "XPBR31", "ITAUSA": "ITSA4", "ITAÚSA": "ITSA4",
        "MAGALU": "MGLU3", "MAGAZINE LUIZA": "MGLU3", "CASAS BAHIA": "BHIA3",
        "PETROBRAS": "PETR4", "PETROBRÁS": "PETR4", "VALE": "VALE3",
        "WEG": "WEGE3", "SUZANO": "SUZB3", "GERDAU": "GGBR4",
        "ELETROBRAS": "ELET3", "ELETROBRÁS": "ELET3", "TAESA": "TAEE11"
    }

    ticker = de_para.get(nome, nome)

    if not ticker.endswith(".SA") and not ticker.endswith("34"):
        ticker += ".SA"

    return ticker


@st.cache_data
def buscar_dados(ticker, inicio, fim):
    df = yf.download(ticker, start=inicio, end=fim, progress=False)
    if df.empty:
        raise ValueError("Nenhum dado encontrado.")
    return df


@st.cache_data
def buscar_dividendos(ticker, inicio, fim):
    t = yf.Ticker(ticker)
    divs = t.dividends
    return divs.loc[str(inicio):str(fim)]


def calcular_resultado(df, coluna, qtd, corretagem, divs):
    p_compra = float(df[coluna].iloc[0])
    p_venda = float(df[coluna].iloc[-1])

    investido = (p_compra * qtd) + corretagem
    venda = (p_venda * qtd) - corretagem
    total_divs = float(divs.sum() * qtd)

    lucro = (venda - investido) + total_divs
    rentab = (lucro / investido) * 100

    return investido, venda, total_divs, lucro, rentab


# =========================
# SIDEBAR
# =========================
st.sidebar.header("📊 Configurações")

input_usuario = st.sidebar.text_input("Ativo ou Empresa", "PETR4")
ticker = tratar_ticker(input_usuario)

data_inicio = st.sidebar.date_input("Data de Compra", datetime(2023, 1, 1))
data_fim = st.sidebar.date_input("Data de Venda", datetime.today())

qtd_acoes = st.sidebar.number_input("Quantidade", min_value=1, value=100)
corretagem = st.sidebar.number_input("Corretagem (R$)", min_value=0.0, value=4.50)

# Validação básica
if data_inicio >= data_fim:
    st.error("A data de início deve ser menor que a data final.")
    st.stop()

# =========================
# EXECUÇÃO
# =========================
try:
    df = buscar_dados(ticker, data_inicio, data_fim)

    # Corrigir MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    coluna = "Adj Close" if "Adj Close" in df.columns else "Close"

    divs = buscar_dividendos(ticker, data_inicio, data_fim)

    investido, venda, total_divs, lucro, rentab = calcular_resultado(
        df, coluna, qtd_acoes, corretagem, divs
    )

    # =========================
    # UI
    # =========================
    st.title(f"📈 Simulação: {ticker.replace('.SA','')}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Investido", f"R$ {investido:,.2f}")
    c2.metric("💸 Venda", f"R$ {venda:,.2f}")
    c3.metric("🎁 Dividendos", f"R$ {total_divs:,.2f}")
    c4.metric("📊 Lucro", f"R$ {lucro:,.2f}", f"{rentab:.2f}%")

    # =========================
    # GRÁFICO
    # =========================
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df[coluna],
        mode='lines',
        name='Preço'
    ))

    fig.update_layout(
        template="plotly_dark",
        title="Evolução do Preço",
        xaxis_title="Data",
        yaxis_title="Preço (R$)"
    )

    st.plotly_chart(fig, use_container_width=True)

    # =========================
    # TABELA EXTRA
    # =========================
    with st.expander("Ver dados históricos"):
        st.dataframe(df.tail(50))

except Exception as e:
    st.error(f"Erro: {str(e)}")
