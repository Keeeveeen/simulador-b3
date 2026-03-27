import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# 1. Configurações de Página
st.set_page_config(page_title="Simulador B3 Quant", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0b0e11; color: #ffffff; }
    [data-testid="stMetric"] {
        background-color: #15191c;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #2d3239;
    }
    .status-card {
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        border-left: 5px solid #34a853;
        background-color: #1a221b;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. Sidebar com Parâmetros
with st.sidebar:
    st.header("Análise Quantitativa")
    busca = st.text_input("Ativo (Ex: PETR4, VALE3, ITUB4)", "PETR4").strip().upper()
    ticker = f"{busca}.SA" if not busca.endswith(".SA") else busca
    
    st.divider()
    data_compra = st.date_input("Início", value=pd.to_datetime("2023-01-01"), format="DD/MM/YYYY")
    data_venda = st.date_input("Fim", value=datetime.now(), format="DD/MM/YYYY")
    
    st.divider()
    qtd = st.number_input("Quantidade", min_value=1, value=100)
    taxa = st.number_input("Corretagem (R$)", value=0.0)
    selic = st.number_input("Selic Atual (% aa)", value=10.75)

# 3. Processamento de Dados
@st.cache_data(ttl=3600)
def get_quant_data(ticker, start, end):
    stock = yf.Ticker(ticker)
    df = stock.history(start=start, end=end)
    ibov = yf.download("^BVSP", start=start, end=end, progress=False)
    return df, ibov

try:
    df, ibov = get_quant_data(ticker, data_compra, data_venda)

    if not df.empty:
        # --- REPARO TÉCNICO (FIX 1D VECTOR) ---
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        if isinstance(ibov.columns, pd.MultiIndex):
            ibov.columns = ibov.columns.get_level_values(0)

        # Garantindo vetores 1D limpos para o Plotly
        precos_acao = df['Close'].squeeze()
        precos_ibov = ibov['Close'].squeeze()
        dividendos_serie = df['Dividends'].squeeze()

        # --- CÁLCULOS ---
        p_ini, p_fim = float(precos_acao.iloc[0]), float(precos_acao.iloc[-1])
        div_total = dividendos_serie.sum() * qtd
        investido = p_ini * qtd
        bruto = p_fim * qtd
        lucro_cap = bruto - investido
        liq = lucro_cap + div_total - (taxa * 2) - max(0, lucro_cap * 0.15 if lucro_cap > 0 else 0)
        rent_total = (liq / investido) * 100
        
        # Drawdown
        cum_max = precos_acao.cummax()
        drawdown = (precos_acao - cum_max) / cum_max
        max_drawdown = drawdown.min() * 100
        
        # Beta e Sharpe
        ret_acao = precos_acao.pct_change().dropna()
        ret_ibov = precos_ibov.pct_change().dropna()
        comum = ret_acao.index.intersection(ret_ibov.index)
        beta = np.polyfit(ret_ibov[comum], ret_acao[comum], 1)[0]
        
        vol = ret_acao.std() * np.sqrt(252) * 100
        rent_ibov = ((precos_ibov.iloc[-1] / precos_ibov.iloc[0]) - 1) * 100

        # --- INTERFACE ---
        st.title(f"Intelligence Dashboard: {busca}")
        
        if rent_total > rent_ibov:
            st.markdown(f'<div class="status-card">🚀 <b>Alpha Positivo:</b> Superou o mercado em {(rent_total - rent_ibov):.2f}%.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="status-card" style="border-left-color: #ea4335; background-color: #251a1a;">⚠️ <b>Underperformance:</b> Abaixo do índice de referência.</div>', unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        fmt = lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        m1.metric("Resultado Final", fmt(investido + liq), delta=f"{rent_total:.2f}%")
        m2.metric("Dividendos", fmt(div_total))
        m3.metric("Max Drawdown", f"{max_drawdown:.2f}%", delta_color="inverse")
        m4.metric("Beta (vs Ibov)", f"{beta:.2f}")

        tab1, tab2 = st.tabs(["📊 Performance Comparada", "📉 Análise de Risco"])
        
        with tab1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=precos_acao.index, y=(precos_acao/p_ini)*100, name=busca, line=dict(color='#34a853', width=3)))
            fig.add_trace(go.Scatter(x=precos_ibov.index, y=(precos_ibov/precos_ibov.iloc[0])*100, name="IBOVESPA", line=dict(color='#5f6368', dash='dot')))
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=10,b=0), xaxis=dict(fixedrange=True), yaxis=dict(side="right", fixedrange=True, ticksuffix="%"))
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            fig_dd = go.Figure()
            fig_dd.add_trace(go.Scatter(x=drawdown.index, y=drawdown*100, fill='tozeroy', name="Drawdown", line=dict(color='#ea4335')))
            fig_dd.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(side="right", ticksuffix="%", fixedrange=True), xaxis=dict(fixedrange=True))
            st.plotly_chart(fig_dd, use_container_width=True)

except Exception as e:
    st.error(f"Erro técnico ao processar: {e}")
