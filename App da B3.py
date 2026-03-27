import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
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
    busca = st.text_input("Ativo (Ex: PETR4, VALE3)", "PETR4").strip().upper()
    ticker = f"{busca}.SA" if not busca.endswith(".SA") else busca
    
    st.divider()
    data_compra = st.date_input("Data de Compra", value=pd.to_datetime("2023-01-01"))
    # Força a data final para 2 dias atrás para garantir que o Yahoo Finance tenha os dados fechados
    data_venda = st.date_input("Data de Venda", value=datetime.now() - timedelta(days=2))
    
    st.divider()
    qtd = st.number_input("Quantidade de Ações", min_value=1, value=100)
    taxa = st.number_input("Corretagem por Ordem (R$)", value=4.50)

# 3. Função de Coleta Segura
def get_safe_data(t, start, end):
    try:
        s = yf.Ticker(t)
        d = s.history(start=start, end=end)
        i = yf.download("^BVSP", start=start, end=end, progress=False)
        return d, i, s.news
    except:
        return pd.DataFrame(), pd.DataFrame(), []

df_acao, df_ibov, news = get_safe_data(ticker, data_compra, data_venda)

# 4. Validação e Cálculos
if df_acao.empty or len(df_acao) < 2:
    st.warning("⚠️ Dados insuficientes. Tente aumentar o período ou mudar o ativo.")
else:
    # Ajuste de Colunas
    if isinstance(df_acao.columns, pd.MultiIndex): df_acao.columns = df_acao.columns.get_level_values(0)
    
    # Preços e Cálculos
    precos = df_acao['Close'].dropna()
    p_ini, p_fim = float(precos.iloc[0]), float(precos.iloc[-1])
    
    investido = p_ini * qtd
    valor_final = p_fim * qtd
    dividendos = df_acao['Dividends'].sum() * qtd
    resultado = (valor_final - investido) + dividendos - (taxa * 2)
    rent_perc = (resultado / investido) * 100

    # Layout de Métricas
    st.title(f"Análise de Performance: {busca}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Investido", f"R$ {investido:,.2f}")
    c2.metric("Dividendos", f"R$ {dividendos:,.2f}")
    c3.metric("Lucro/Prejuízo Líquido", f"R$ {resultado:,.2f}", delta=f"{rent_perc:.2f}%")

    # Gráfico de Preço
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=precos.index, y=precos, name="Preço de Fechamento", line=dict(color='#34a853')))
    fig.update_layout(template="plotly_dark", margin=dict(l=0,r=0,t=20,b=0), height=400)
    st.plotly_chart(fig, use_container_width=True)

    # 5. IA GEMINI
    st.divider()
    if st.button("✨ Gerar Insight com IA"):
        with st.spinner("O Gemini está analisando o mercado..."):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                contexto_noticias = [n['title'] for n in news[:3]] if news else ["Nenhuma notícia encontrada."]
                prompt = f"Ação {busca}. Rentabilidade {rent_perc:.2f}%. Notícias: {contexto_noticias}. Explique os motivos dessa
