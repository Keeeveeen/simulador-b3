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
    # Garantindo que a data de venda seja sempre 2 dias atrás para evitar erro de dados vazios
    data_padrao_fim = datetime.now() - timedelta(days=2)
    data_compra = st.date_input("Data de Compra", value=pd.to_datetime("2023-01-01"))
    data_venda = st.date_input("Data de Venda", value=data_padrao_fim)
    
    st.divider()
    qtd = st.number_input("Quantidade de Ações", min_value=1, value=100)
    taxa = st.number_input("Corretagem por Ordem (R$)", value=4.50)

# 3. Coleta de Dados
@st.cache_data(ttl=3600)
def get_data(t, start, end):
    try:
        s = yf.Ticker(t)
        d = s.history(start=start, end=end)
        try: n = s.news
        except: n = []
        return d, n
    except:
        return pd.DataFrame(), []

df_acao, news = get_data(ticker, data_compra, data_venda)

# 4. Validação e Dashboard
if df_acao.empty or len(df_acao) < 2:
    st.warning("⚠️ Sem dados suficientes. Tente recuar a 'Data de Venda' ou mudar o ativo.")
else:
    # Limpeza de colunas
    if isinstance(df_acao.columns, pd.MultiIndex): 
        df_acao.columns = df_acao.columns.get_level_values(0)
    
    precos = df_acao['Close'].dropna()
    p_ini, p_fim = float(precos.iloc[0]), float(precos.iloc[-1])
    
    # Cálculos
    investido = p_ini * qtd
    valor_final = p_fim * qtd
    dividendos = df_acao['Dividends'].sum() * qtd
    lucro_liquido = (valor_final - investido) + dividendos - (taxa * 2)
    rent_perc = (lucro_liquido / investido) * 100

    # Interface
    st.title(f"Dashboard: {busca}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Investido", f"R$ {investido:,.2f}")
    c2.metric("Dividendos", f"R$ {dividendos:,.2f}")
    c3.metric("Lucro Líquido", f"R$ {lucro_liquido:,.2f}", delta=f"{rent_perc:.2f}%")

    # Gráfico
    fig = go.Figure(go.Scatter(x=precos.index, y=precos, name="Preço", line=dict(color='#34a853')))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=20,b=0))
    st.plotly_chart(fig, use_container_width=True)

    # 5. IA GEMINI (Reparo de Versão)
    st.divider()
    if st.button("✨ Gerar Insight com Gemini IA"):
        with st.spinner("IA analisando..."):
            # Prompt unificado
            titulos = [n.get('title', 'Notícia') for n in news[:3]] if news else ["Sem notícias."]
            prompt = f"Ação {busca}. Rentabilidade {rent_perc:.2f}%. Notícias: {titulos}. Explique a variação como um economista."
            
            # Tentativa Sequencial de Modelos para evitar o Erro 404
            success = False
            for model_name in ['gemini-1.5-flash', 'gemini-pro']:
                if success: break
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    st.info(f"**Análise ({model_name}):**\n\n{response.text}")
                    success = True
                except Exception as e:
                    continue
            
            if not success:
                st.error("Não foi possível conectar aos modelos Gemini. Verifique se a sua chave API ainda é válida no Google AI Studio.")
