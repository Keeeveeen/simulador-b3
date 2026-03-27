import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configurações iniciais
st.set_page_config(page_title="Simulador B3 Pro", layout="wide", initial_sidebar_state="collapsed")

# Estilização Google Finance Dark
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500&display=swap');
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
    .stApp { background-color: #101214; color: #e8eaed; }
    [data-testid="stMetric"] {
        background-color: #1a1c1e;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #2d3033;
    }
    .company-header { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .company-logo { width: 48px; height: 48px; border-radius: 8px; background-color: white; padding: 4px; }
    </style>
    """, unsafe_allow_html=True)

# Dicionário simples para Logos (Domínios das empresas)
logos_db = {
    "PETR4": "petrobras.com.br", "VALE3": "vale.com", "ITUB4": "itau.com.br",
    "BBAS3": "bb.com.br", "BBDC4": "bradesco.com.br", "MGLU3": "magazineluiza.com.br",
    "ABEV3": "ambev.com.br", "WEGE3": "weg.net"
}

with st.sidebar:
    st.header("Configurações")
    ticker_raw = st.text_input("Ação (ex: VALE3, PETR4)", "PETR4").strip().upper()
    ticker = f"{ticker_raw}.SA" if not ticker_raw.endswith(".SA") else ticker_raw
    quantidade = st.number_input("Quantidade", min_value=1, value=100)
    corretagem = st.number_input("Corretagem (R$)", value=0.0)
    
    st.divider()
    periodo = st.selectbox("Período", ["1 Dia", "1 Mês", "6 Meses", "1 Ano", "5 Anos", "Personalizado"], index=4)

# Lógica de Datas e Intervalo
hoje = datetime.now()
intervalo = "1d"

if periodo == "1 Dia":
    data_inicio = hoje - timedelta(days=3) # Pega 3 dias para garantir que pegue o último pregão aberto
    data_fim = hoje
    intervalo = "1h" # Ativa flutuação por hora
elif periodo == "1 Mês": data_inicio = hoje - timedelta(days=30); data_fim = hoje
elif periodo == "6 Meses": data_inicio = hoje - timedelta(days=180); data_fim = hoje
elif periodo == "1 Ano": data_inicio = hoje - timedelta(days=365); data_fim = hoje
elif periodo == "5 Anos": data_inicio = hoje - timedelta(days=365*5); data_fim = hoje
else:
    col_d1, col_d2 = st.columns(2)
    data_inicio = col_d1.date_input("Início", value=pd.to_datetime("2023-01-01"))
    data_fim = col_d2.date_input("Fim", value=hoje)

# Busca de Dados
df = yf.download(ticker, start=data_inicio, end=data_fim, interval=intervalo, progress=False)
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

if not df.empty:
    # Se for "1 Dia", filtramos apenas o último dia disponível com dados
    if periodo == "1 Dia":
        ultimo_dia = df.index[-1].date()
        df = df[df.index.date == ultimo_dia]

    # Header com Logo
    domain = logos_db.get(ticker_raw, "google.com") # Default google se não estiver no db
    logo_url = f"https://logo.clearbit.com/{domain}"
    
    st.markdown(f"""
        <div class="company-header">
            <img src="{logo_url}" class="company-logo">
            <h1 style="margin:0;">{ticker_raw}</h1>
        </div>
    """, unsafe_allow_html=True)

    # Cálculos e Métricas (Simplificados 2 casas)
    p_compra, p_venda = float(df['Close'].iloc[0]), float(df['Close'].iloc[-1])
    inv, bruto = p_compra * quantidade, p_venda * quantidade
    liq = (bruto - inv) - (corretagem * 2) - max(0, (bruto-inv)*0.15 if bruto > inv else 0)
    rent = (liq / inv) * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("Investido", f"R$ {inv:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("Valor Final", f"R$ {bruto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c3.metric("Lucro Líquido", f"R$ {liq:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), delta=f"{rent:.2f}%")

    # Gráfico Estilo Google (Trava de Range)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'], mode='lines',
        line=dict(color='#34a853' if liq >= 0 else '#ea4335', width=2),
        fill='tozeroy', fillcolor='rgba(52, 168, 83, 0.05)' if liq >= 0 else 'rgba(234, 67, 53, 0.05)',
        hovertemplate='<b>%{y:.2f} BRL</b><extra></extra>'
    ))

    fig.update_layout(
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0),
        hovermode="x unified",
        xaxis=dict(
            showgrid=False, 
            tickformat="%H:%M" if periodo == "1 Dia" else "%d/%m/%y",
            range=[df.index[0], df.index[-1]], # TRAVA O GRÁFICO AQUI
            fixedrange=False # Permite zoom, mas o range inicial e final limitam o scroll
        ),
        yaxis=dict(side="right", gridcolor='#2d3033', tickprefix="R$ "),
        height=450
    )
    # Impede de puxar para os lados além dos dados
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])]) # Pula fins de semana

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
