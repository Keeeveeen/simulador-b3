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
    # Ajuste automático para evitar erros de dados do dia atual
    data_max = datetime.now() - timedelta(days=1)
    data_compra = st.date_input("Data de Compra", value=pd.to_datetime("2023-01-01"))
    data_venda = st.date_input("Data de Venda", value=data_max)
    
    st.divider()
    qtd = st.number_input("Quantidade de Ações", min_value=1, value=100)
    taxa = st.number_input("Corretagem por Ordem (R$)", value=4.50)

# 3. Coleta de Dados Blindada
def get_safe_data(t, start, end):
    try:
        s = yf.Ticker(t)
        d = s.history(start=start, end=end)
        # Notícias são opcionais, se falhar o código segue
        try: n = s.news
        except: n = []
        return d, n
    except:
        return pd.DataFrame(), []

df_acao, news = get_safe_data(ticker, data_compra, data_venda)

# 4. Validação e Renderização
if df_acao.empty or len(df_acao) < 2:
    st.warning("⚠️ Dados insuficientes no Yahoo Finance para este período. Tente mudar as datas.")
else:
    # Correção de Colunas
    if isinstance(df_acao.columns, pd.MultiIndex): 
        df_acao.columns = df_acao.columns.get_level_values(0)
    
    precos = df_acao['Close'].dropna()
    p_ini, p_fim = float(precos.iloc[0]), float(precos.iloc[-1])
    
    # Cálculos Financeiros
    investido = p_ini * qtd
    valor_final_acao = p_fim * qtd
    dividendos = df_acao['Dividends'].sum() * qtd
    resultado = (valor_final_acao - investido) + dividendos - (taxa * 2)
    rent_perc = (resultado / investido) * 100

    # Dashboard Principal
    st.title(f"Dashboard de Trading: {busca}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Investido", f"R$ {investido:,.2f}")
    c2.metric("Dividendos", f"R$ {dividendos:,.2f}")
    c3.metric("Lucro Líquido", f"R$ {resultado:,.2f}", delta=f"{rent_perc:.2f}%")

    # Gráfico de Performance
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=precos.index, y=precos, name="Preço", line=dict(color='#34a853', width=2)))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # 5. IA GEMINI (Agora com a string corrigida)
    st.divider()
    if st.button("✨ Gerar Insight com Gemini IA"):
        with st.spinner("O Gemini está analisando os motivos do mercado..."):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                contexto_noticias = [n.get('title', 'Notícia sem título') for n in news[:3]] if news else ["Nenhuma notícia encontrada."]
                
                # STRING CORRIGIDA ABAIXO (Faltava fechar aspas ou quebra de linha)
                prompt = f"Analise o ativo {busca}. Retorno: {rent_perc:.2f}%. Notícias: {contexto_noticias}. Como economista, explique brevemente o porquê dessa variação."
                
                response = model.generate_content(prompt)
                st.info(response.text)
            except Exception as e:
                st.error(f"Erro na IA: {str(e)}")
