import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import google.generativeai as genai

# 1. CONFIGURAÇÃO DA CHAVE PADRÃO
# Se o erro persistir, verifique sua chave no Google AI Studio
GOOGLE_API_KEY = "AIzaSyAsguDdDiNoiWYaJjWcFBuMErwIpBaEfxw"
genai.configure(api_key=GOOGLE_API_KEY)

# 2. Configurações de Página
st.set_page_config(page_title="Simulador B3 Ultra + Gemini", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: #ffffff; }
    [data-testid="stMetric"] { background-color: #15191c; padding: 20px; border-radius: 12px; border: 1px solid #2d3239; }
    </style>
    """, unsafe_allow_html=True)

# 3. Sidebar - Parâmetros de Simulação
with st.sidebar:
    st.header("Configurações")
    busca = st.text_input("Ativo (Ex: PETR4, VALE3)", "PETR4").strip().upper()
    ticker = f"{busca}.SA" if not busca.endswith(".SA") else busca
    
    st.divider()
    # Data final padrão em D-2 para garantir fechamento de mercado
    data_padrao_fim = datetime.now() - timedelta(days=2)
    data_compra = st.date_input("Data de Compra", value=pd.to_datetime("2023-01-01"))
    data_venda = st.date_input("Data de Venda", value=data_padrao_fim)
    
    st.divider()
    qtd = st.number_input("Quantidade de Ações", min_value=1, value=100)
    taxa = st.number_input("Corretagem por Ordem (R$)", value=4.50)

# 4. Coleta de Dados
@st.cache_data(ttl=3600)
def get_market_data(t, start, end):
    try:
        s = yf.Ticker(t)
        d = s.history(start=start, end=end)
        try: n = s.news
        except: n = []
        return d, n
    except:
        return pd.DataFrame(), []

df_acao, news = get_market_data(ticker, data_compra, data_venda)

# 5. Validação e Dashboard
if df_acao.empty or len(df_acao) < 2:
    st.warning("⚠️ Dados insuficientes. Tente mudar as datas ou o ativo.")
else:
    # Ajuste de Colunas MultiIndex
    if isinstance(df_acao.columns, pd.MultiIndex): 
        df_acao.columns = df_acao.columns.get_level_values(0)
    
    precos = df_acao['Close'].dropna()
    p_ini, p_fim = float(precos.iloc[0]), float(precos.iloc[-1])
    
    # Cálculos Financeiros (Quantidade e Taxas inclusas)
    investido = p_ini * qtd
    valor_final = p_fim * qtd
    dividendos = df_acao['Dividends'].sum() * qtd
    lucro_liquido = (valor_final - investido) + dividendos - (taxa * 2)
    rent_perc = (lucro_liquido / investido) * 100

    # Layout de Métricas
    st.title(f"Dashboard: {busca}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Investido", f"R$ {investido:,.2f}")
    c2.metric("Dividendos", f"R$ {dividendos:,.2f}")
    c3.metric("Lucro Líquido", f"R$ {lucro_liquido:,.2f}", delta=f"{rent_perc:.2f}%")

    # Gráfico de Performance
    fig = go.Figure(go.Scatter(x=precos.index, y=precos, name="Preço", line=dict(color='#34a853', width=2)))
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=20,b=0))
    st.plotly_chart(fig, use_container_width=True)

    # 6. IA GEMINI (Versão de Diagnóstico Final)
    st.divider()
    if st.button("✨ Gerar Insight com Gemini IA"):
        with st.spinner("Analisando com a IA..."):
            try:
                # Tentando o modelo padrão estável
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Preparando o contexto
                titulos = [n.get('title', 'Notícia') for n in news[:3]] if news else ["Sem notícias recentes."]
                prompt = (f"Como um economista sênior, analise a performance da {busca}. "
                         f"Rentabilidade de {rent_perc:.2f}% no período selecionado. "
                         f"Notícias recentes: {titulos}. Explique os motivos dessa variação de forma concisa.")
                
                response = model.generate_content(prompt)
                
                if response.text:
                    st.info(f"**Análise do Especialista Gemini:**\n\n{response.text}")
                else:
                    st.warning("A IA processou o pedido, mas não retornou texto (pode ser um filtro de segurança).")

            except Exception as e:
                # Aqui ele vai imprimir o erro real se a chave falhar
                st.error(f"Erro detalhado na conexão com a IA: {str(e)}")
                st.write("Verifique se sua API Key no topo do código ainda é válida.")
