import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import openai

# 1. Configurações de Página
st.set_page_config(page_title="Simulador B3 Quant + IA", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0b0e11; color: #ffffff; }
    [data-testid="stMetric"] { background-color: #15191c; padding: 20px; border-radius: 12px; border: 1px solid #2d3239; }
    .status-card { padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #34a853; background-color: #1a221b; }
    </style>
    """, unsafe_allow_html=True)

# 2. Sidebar
with st.sidebar:
    st.header("Análise Quantitativa & IA")
    busca = st.text_input("Ativo (Ex: PETR4, VALE3)", "PETR4").strip().upper()
    ticker = f"{busca}.SA" if not busca.endswith(".SA") else busca
    
    st.divider()
    data_compra = st.date_input("Início", value=pd.to_datetime("2023-01-01"), format="DD/MM/YYYY")
    data_venda = st.date_input("Fim", value=datetime.now() - timedelta(days=1), format="DD/MM/YYYY")
    
    st.divider()
    qtd = st.number_input("Quantidade", min_value=1, value=100)
    api_key = st.text_input("Chave API OpenAI", type="password", help="Insira sua chave para habilitar a análise de IA")

# 3. Processamento de Dados
@st.cache_data(ttl=3600)
def get_quant_data(ticker, start, end):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start, end=end)
        ibov = yf.download("^BVSP", start=start, end=end, progress=False)
        return df, ibov, stock.news
    except:
        return pd.DataFrame(), pd.DataFrame(), []

try:
    df, ibov, news = get_quant_data(ticker, data_compra, data_venda)

    if not df.empty and len(df) >= 2:
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        if isinstance(ibov.columns, pd.MultiIndex): ibov.columns = ibov.columns.get_level_values(0)

        precos_acao = df['Close'].dropna().squeeze()
        precos_ibov = ibov['Close'].dropna().squeeze()
        
        common_index = precos_acao.index.intersection(precos_ibov.index)
        precos_acao = precos_acao.loc[common_index]
        precos_ibov = precos_ibov.loc[common_index]

        p_ini, p_fim = float(precos_acao.iloc[0]), float(precos_acao.iloc[-1])
        div_total = df['Dividends'].loc[common_index].sum() * qtd
        rent_total = (((p_fim * qtd + div_total) / (p_ini * qtd)) - 1) * 100
        rent_ibov = ((precos_ibov.iloc[-1] / precos_ibov.iloc[0]) - 1) * 100

        # Interface
        st.title(f"Intelligence Dashboard: {busca}")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Resultado Final", f"R$ {(p_ini * qtd + (p_fim - p_ini) * qtd + div_total):,.2f}", delta=f"{rent_total:.2f}%")
        m2.metric("Dividendos", f"R$ {div_total:,.2f}")
        m3.metric("Benchmark Ibov", f"{rent_ibov:.2f}%")

        # Gráfico
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=precos_acao.index, y=(precos_acao/p_ini)*100, name=busca, line=dict(color='#34a853', width=3)))
        fig.add_trace(go.Scatter(x=precos_ibov.index, y=(precos_ibov/precos_ibov.iloc[0])*100, name="IBOVESPA", line=dict(color='#5f6368', dash='dot')))
        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=20,b=0), xaxis=dict(fixedrange=True), yaxis=dict(side="right", ticksuffix="%", fixedrange=True))
        st.plotly_chart(fig, use_container_width=True)

        # SEÇÃO DE IA
        st.divider()
        st.subheader("🤖 Parecer do Analista IA")
        
        if api_key:
            if st.button("Gerar Análise com IA"):
                with st.spinner("Analisando notícias e fundamentos..."):
                    try:
                        client = openai.OpenAI(api_key=api_key)
                        headlines = [n['title'] for n in news[:5]]
                        prompt = f"Analise o ativo {busca}. Retorno: {rent_total:.2f}% vs Ibov: {rent_ibov:.2f}%. Notícias: {headlines}. Explique resumidamente o motivo da variação."
                        
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "user", "content": prompt}]
                        )
                        st.info(response.choices[0].message.content)
                    except Exception as e:
                        st.error(f"Erro na IA: {e}")
        else:
            st.warning("Insira sua Chave API na barra lateral para habilitar a análise de IA.")

except Exception as e:
    st.error(f"Erro ao processar: {e}")
