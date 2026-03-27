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
        padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #34a853; background-color: #1a221b;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. Sidebar
with st.sidebar:
    st.header("Análise Quantitativa")
    busca = st.text_input("Ativo (Ex: PETR4, VALE3)", "PETR4").strip().upper()
    ticker = f"{busca}.SA" if not busca.endswith(".SA") else busca
    
    st.divider()
    # Ajuste: Garantindo que a data final seja sempre o dia anterior para evitar vetores vazios hoje
    data_compra = st.date_input("Início", value=pd.to_datetime("2023-01-01"), format="DD/MM/YYYY")
    data_venda = st.date_input("Fim", value=datetime.now() - timedelta(days=1), format="DD/MM/YYYY")
    
    st.divider()
    qtd = st.number_input("Quantidade", min_value=1, value=100)
    taxa = st.number_input("Corretagem (R$)", value=0.0)
    selic = st.number_input("Selic Atual (% aa)", value=10.75)

# 3. Processamento de Dados com Tratamento de Erro de Vetor Vazio
@st.cache_data(ttl=3600)
def get_quant_data(ticker, start, end):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start, end=end)
        ibov = yf.download("^BVSP", start=start, end=end, progress=False)
        return df, ibov
    except:
        return pd.DataFrame(), pd.DataFrame()

try:
    df, ibov = get_quant_data(ticker, data_compra, data_venda)

    # VALIDAÇÃO CRÍTICA: Se o DataFrame for vazio, nem tenta gerar o gráfico
    if df is None or df.empty or len(df) < 2:
        st.error(f"Sem dados suficientes para {busca} no período selecionado. Tente mudar as datas.")
    else:
        # Achata colunas MultiIndex se existirem
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        if isinstance(ibov.columns, pd.MultiIndex): ibov.columns = ibov.columns.get_level_values(0)

        # Garante vetores 1D e remove valores nulos (NaN) que causam o bug do Plotly
        precos_acao = df['Close'].dropna().squeeze()
        precos_ibov = ibov['Close'].dropna().squeeze()
        
        # Sincroniza os índices (Datas) para evitar vetores de tamanhos diferentes
        common_index = precos_acao.index.intersection(precos_ibov.index)
        if len(common_index) < 2:
            st.warning("Poucos dados em comum com o Ibovespa para análise de comparação.")
            precos_ibov_resampled = precos_acao # Fallback para não crashar
        else:
            precos_acao = precos_acao.loc[common_index]
            precos_ibov_resampled = precos_ibov.loc[common_index]

        # --- CÁLCULOS ---
        p_ini, p_fim = float(precos_acao.iloc[0]), float(precos_acao.iloc[-1])
        div_total = df['Dividends'].loc[common_index].sum() * qtd
        liq = ((p_fim - p_ini) * qtd) + div_total - (taxa * 2)
        rent_total = (liq / (p_ini * qtd)) * 100
        rent_ibov = ((precos_ibov_resampled.iloc[-1] / precos_ibov_resampled.iloc[0]) - 1) * 100

        # --- INTERFACE ---
        st.title(f"Intelligence Dashboard: {busca}")
        
        m1, m2, m3 = st.columns(3)
        fmt = lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        m1.metric("Resultado Final", fmt((p_ini * qtd) + liq), delta=f"{rent_total:.2f}%")
        m2.metric("Dividendos", fmt(div_total))
        m3.metric("Retorno Ibov", f"{rent_ibov:.2f}%")

        tab1, tab2 = st.tabs(["📊 Performance", "📉 Drawdown"])
        
        with tab1:
            fig = go.Figure()
            # O Plotly precisa de dados limpos. Reset_index garante que o eixo X seja legível.
            fig.add_trace(go.Scatter(x=precos_acao.index, y=(precos_acao/p_ini)*100, name=busca, line=dict(color='#34a853', width=3)))
            fig.add_trace(go.Scatter(x=precos_ibov_resampled.index, y=(precos_ibov_resampled/precos_ibov_resampled.iloc[0])*100, name="IBOVESPA", line=dict(color='#5f6368', dash='dot')))
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=10,b=0), xaxis=dict(fixedrange=True), yaxis=dict(side="right", fixedrange=True, ticksuffix="%"))
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            cum_max = precos_acao.cummax()
            drawdown = (precos_acao - cum_max) / cum_max
            fig_dd = go.Figure()
            fig_dd.add_trace(go.Scatter(x=drawdown.index, y=drawdown*100, fill='tozeroy', name="Drawdown", line=dict(color='#ea4335')))
            fig_dd.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(side="right", ticksuffix="%", fixedrange=True))
            st.plotly_chart(fig_dd, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao processar: {e}")
