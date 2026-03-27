import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import google.generativeai as genai # BIBLIOTECA DO GOOGLE

# 1. Configurações de Página
st.set_page_config(page_title="Simulador B3 + Gemini IA", layout="wide", initial_sidebar_state="expanded")

# (O CSS de estilo continua o mesmo das versões anteriores...)

# 2. Sidebar
with st.sidebar:
    st.header("Configurações")
    busca = st.text_input("Ativo", "PETR4").strip().upper()
    ticker = f"{busca}.SA" if not busca.endswith(".SA") else busca
    
    data_compra = st.date_input("Início", value=pd.to_datetime("2023-01-01"))
    data_venda = st.date_input("Fim", value=datetime.now() - timedelta(days=1))
    
    st.divider()
    # CAMPO PARA VOCÊ COLAR A CHAVE DO GOOGLE (AIza...)
    google_key = st.text_input("Google API Key", type="password")

# 3. Lógica de Dados (Mesma das versões anteriores com correção de vetores)
@st.cache_data(ttl=3600)
def get_data(ticker, start, end):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start, end=end)
        ibov = yf.download("^BVSP", start=start, end=end, progress=False)
        return df, ibov, stock.news
    except: return pd.DataFrame(), pd.DataFrame(), []

try:
    df, ibov, news = get_data(ticker, data_compra, data_venda)

    if not df.empty and len(df) >= 2:
        # Limpeza de dados para evitar erro de vetor vazio
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        precos_acao = df['Close'].dropna().squeeze()
        p_ini, p_fim = float(precos_acao.iloc[0]), float(precos_acao.iloc[-1])
        rent_total = ((p_fim / p_ini) - 1) * 100

        # Interface Gráfica
        st.title(f"Dashboard Quantitativo: {busca}")
        st.metric("Rentabilidade no Período", f"{rent_total:.2f}%")
        
        fig = go.Figure(go.Scatter(x=precos_acao.index, y=(precos_acao/p_ini)*100, name=busca, line=dict(color='#34a853')))
        fig.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig, use_container_width=True)

        # --- SEÇÃO DA IA DO GOOGLE (GEMINI) ---
        st.divider()
        st.subheader("🤖 Análise do Especialista Gemini")
        
        if google_key:
            if st.button("Analisar Movimentações com Gemini"):
                with st.spinner("O Gemini está analisando o mercado..."):
                    try:
                        # Configura a IA do Google
                        genai.configure(api_key=google_key)
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        headlines = [n['title'] for n in news[:5]]
                        prompt = f"""
                        Analise o desempenho da ação {busca} na B3.
                        Variação no período: {rent_total:.2f}%.
                        Notícias recentes: {headlines}.
                        
                        Como um economista, explique de forma muito breve (2 parágrafos) 
                        o que pode ter causado essa variação baseando-se nas notícias 
                        ou no cenário macroeconômico brasileiro.
                        """
                        
                        response = model.generate_content(prompt)
                        st.info(response.text)
                    except Exception as e:
                        st.error(f"Erro na IA do Google: {e}")
        else:
            st.warning("Insira sua Google API Key na lateral para habilitar a análise.")

except Exception as e:
    st.error(f"Erro: {e}")
