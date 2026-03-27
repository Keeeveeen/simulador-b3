import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import google.generativeai as genai

# CONFIGURAÇÃO DA CHAVE PADRÃO
GOOGLE_API_KEY = "AIzaSyAsguDdDiNoiWYaJjWcFBuMErwIpBaEfxw"
genai.configure(api_key=GOOGLE_API_KEY)

# 1. Configurações de Página
st.set_page_config(page_title="Simulador B3 Ultra + Gemini", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: #ffffff; }
    [data-testid="stMetric"] { background-color: #15191c; padding: 20px; border-radius: 12px; border: 1px solid #2d3239; }
    </style>
    """, unsafe_allow_html=True)

# 2. Sidebar
with st.sidebar:
    st.header("Configurações")
    busca = st.text_input("Ativo (PETR4, VALE3, etc.)", "PETR4").strip().upper()
    ticker = f"{busca}.SA" if not busca.endswith(".SA") else busca
    
    st.divider()
    # Ajuste automático de data para evitar vetores vazios
    data_padrao_fim = datetime.now() - timedelta(days=1)
    data_compra = st.date_input("Data de Compra", value=pd.to_datetime("2023-01-01"))
    data_venda = st.date_input("Data de Venda", value=data_padrao_fim)
    
    st.divider()
    qtd = st.number_input("Quantidade de Ações", min_value=1, value=100, step=10)
    taxa = st.number_input("Corretagem por Ordem (R$)", value=4.50)

# 3. Coleta de Dados
@st.cache_data(ttl=3600)
def get_market_data(t, start, end):
    try:
        s = yf.Ticker(t)
        d = s.history(start=start, end=end)
        i = yf.download("^BVSP", start=start, end=end, progress=False)
        return d, i, s.news
    except:
        return pd.DataFrame(), pd.DataFrame(), []

# Inicializa variáveis para evitar NameError
df_acao, df_ibov, lista_noticias = get_market_data(ticker, data_compra, data_venda)

# 4. Lógica de Processamento
if df_acao.empty or len(df_acao) < 1:
    st.error(f"❌ Não encontramos dados para {busca}. Verifique o ticker ou as datas.")
else:
    try:
        # Limpeza de colunas (MultiIndex fix)
        if isinstance(df_acao.columns, pd.MultiIndex): df_acao.columns = df_acao.columns.get_level_values(0)
        if isinstance(df_ibov.columns, pd.MultiIndex): df_ibov.columns = df_ibov.columns.get_level_values(0)

        # Sincroniza Datas
        precos_acao = df_acao['Close'].dropna()
        precos_ibov = df_ibov['Close'].dropna()
        datas_comuns = precos_acao.index.intersection(precos_ibov.index)
        
        acao_sync = precos_acao.loc[datas_comuns]
        ibov_sync = precos_ibov.loc[datas_comuns]

        # Cálculos Financeiros (Quantidade e Taxas inclusas)
        p_ini = float(acao_sync.iloc[0])
        p_fim = float(acao_sync.iloc[-1])
        
        investido = p_ini * qtd
        valor_final_acao = p_fim * qtd
        total_dividendos = df_acao['Dividends'].loc[datas_comuns].sum() * qtd
        
        lucro_bruto = valor_final_acao - investido
        custos = taxa * 2
        resultado_liquido = lucro_bruto + total_dividendos - custos
        rentabilidade = (resultado_liquido / investido) * 100
        rent_ibov = ((ibov_sync.iloc[-1] / ibov_sync.iloc[0]) - 1) * 100

        # Interface Visual
        st.title(f"Dashboard: {busca}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Investido", f"R$ {investido:,.2f}")
        c2.metric("Dividendos", f"R$ {total_dividendos:,.2f}")
        c3.metric("Lucro Líquido", f"R$ {resultado_liquido:,.2f}", delta=f"{rentabilidade:.2f}%")
        c4.metric("Performance vs Ibov", f"{(rentabilidade - rent_ibov):+.2f}%")

        # Gráfico
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=acao_sync.index, y=(acao_sync/p_ini)*100, name=busca, line=dict(color='#34a853', width=2)))
        fig.add_trace(go.Scatter(x=ibov_sync.index, y=(ibov_sync/ibov_sync.iloc[0])*100, name="IBOVESPA", line=dict(color='#5f6368', dash='dot')))
        fig.update_layout(template="plotly_dark", height=450, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

        # 5. IA GEMINI
        st.divider()
        if st.button("✨ Analisar com Gemini IA"):
            with st.spinner("IA processando dados econômicos..."):
                model = genai.GenerativeModel('gemini-1.5-flash')
                titulos = [n['title'] for n in lista_noticias[:5]] if lista_noticias else ["Sem notícias."]
                prompt = f"Ação {busca}. Rentabilidade: {rentabilidade:.2f}%. Notícias: {titulos}. Explique a variação."
                response = model.generate_content(prompt)
                st.info(response.text)

    except Exception as e:
        st.warning(f"Ajuste as datas: o mercado pode estar fechado hoje. (Erro: {e})")
