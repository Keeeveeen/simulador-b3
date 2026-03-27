import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import google.generativeai as genai

# CONFIGURAÇÃO DA CHAVE PADRÃO (Oculta para o usuário)
GOOGLE_API_KEY = "AIzaSyAsguDdDiNoiWYaJjWcFBuMErwIpBaEfxw"
genai.configure(api_key=GOOGLE_API_KEY)

# 1. Configurações de Página
st.set_page_config(page_title="Simulador B3 Ultra + Gemini", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0b0e11; color: #ffffff; }
    [data-testid="stMetric"] { background-color: #15191c; padding: 20px; border-radius: 12px; border: 1px solid #2d3239; }
    .status-card { padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #34a853; background-color: #1a221b; }
    </style>
    """, unsafe_allow_html=True)

# 2. Sidebar - PARÂMETROS VOLTARAM
with st.sidebar:
    st.header("Configurações de Simulação")
    busca = st.text_input("Ativo (Ex: PETR4, VALE3)", "PETR4").strip().upper()
    ticker = f"{busca}.SA" if not busca.endswith(".SA") else busca
    
    st.divider()
    data_compra = st.date_input("Data de Compra", value=pd.to_datetime("2023-01-01"))
    data_venda = st.date_input("Data de Venda", value=datetime.now() - timedelta(days=1))
    
    st.divider()
    qtd = st.number_input("Quantidade de Ações", min_value=1, value=100, step=10)
    taxa = st.number_input("Corretagem por Ordem (R$)", value=4.50, step=0.5)

# 3. Coleta de Dados
@st.cache_data(ttl=3600)
def get_full_data(ticker, start, end):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start, end=end)
        ibov = yf.download("^BVSP", start=start, end=end, progress=False)
        return df, ibov, stock.news
    except: return pd.DataFrame(), pd.DataFrame(), []

try:
    df, ibov, news = get_full_data(ticker, data_compra, data_venda)

    if not df.empty and len(df) >= 2:
        # Limpeza MultiIndex
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        if isinstance(ibov.columns, pd.MultiIndex): ibov.columns = ibov.columns.get_level_values(0)

        precos = df['Close'].dropna().squeeze()
        precos_ibov = ibov['Close'].dropna().squeeze()
        
        # Sincronização
        idx = precos.index.intersection(precos_ibov.index)
        precos, precos_ibov = precos.loc[idx], precos_ibov.loc[idx]

        # Cálculos Financeiros
        p_ini, p_fim = float(precos.iloc[0]), float(precos.iloc[-1])
        investido = p_ini * qtd
        bruto = p_fim * qtd
        dividendos = df['Dividends'].loc[idx].sum() * qtd
        lucro_liquido = (bruto - investido) + dividendos - (taxa * 2)
        rent_perc = (lucro_liquido / investido) * 100
        rent_ibov = ((precos_ibov.iloc[-1] / precos_ibov.iloc[0]) - 1) * 100

        # Interface
        st.title(f"Dashboard Quantitativo: {busca}")
        
        c1, c2, c3, c4 = st.columns(4)
        def fmt(v): return f"R$ {v:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
        c1.metric("Total Investido", fmt(investido))
        c2.metric("Valor Final + Div", fmt(bruto + dividendos))
        c3.metric("Lucro Líquido", fmt(lucro_liquido), delta=f"{rent_perc:.2f}%")
        c4.metric("Vs Ibovespa", f"{(rent_perc - rent_ibov):+.2f}%")

        # Gráfico
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=precos.index, y=(precos/p_ini)*100, name=busca, line=dict(color='#34a853', width=3)))
        fig.add_trace(go.Scatter(x=precos_ibov.index, y=(precos_ibov/precos_ibov.iloc[0])*100, name="IBOVESPA", line=dict(color='#5f6368', dash='dot')))
        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                          margin=dict(l=0,r=0,t=20,b=0), xaxis=dict(fixedrange=True), yaxis=dict(side="right", ticksuffix="%", fixedrange=True))
        st.plotly_chart(fig, use_container_width=True)

        # 4. IA GEMINI (Botão Direto)
        st.divider()
        if st.button("✨ Gerar Insight da IA (Gemini 1.5)"):
            with st.spinner("Analisando fundamentos e notícias..."):
                model = genai.GenerativeModel('gemini-1.5-flash')
                headlines = [n['title'] for n in news[:5]]
                prompt = f"Analise o ativo {busca}. Retorno: {rent_perc:.2f}% vs Ibov: {rent_ibov:.2f}%. Notícias: {headlines}. Explique o motivo da variação como um economista."
                response = model.generate_content(prompt)
                st.info(response.text)

except Exception as e:
    st.error(f"Erro ao processar simulação: {e}")
