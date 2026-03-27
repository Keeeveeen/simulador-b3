import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import google.generativeai as genai

# CONFIGURAÇÃO DA CHAVE PADRÃO (Sua chave do Google AI Studio)
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

# 2. Sidebar - Parâmetros de Simulação
with st.sidebar:
    st.header("Configurações")
    busca = st.text_input("Ativo (Ex: PETR4, VALE3)", "PETR4").strip().upper()
    ticker = f"{busca}.SA" if not busca.endswith(".SA") else busca
    
    st.divider()
    # Ajuste para garantir que a data final tenha dados (D-2)
    data_max = datetime.now() - timedelta(days=2)
    data_compra = st.date_input("Data de Compra", value=pd.to_datetime("2023-01-01"))
    data_venda = st.date_input("Data de Venda", value=data_max)
    
    st.divider()
    qtd = st.number_input("Quantidade de Ações", min_value=1, value=100)
    taxa = st.number_input("Corretagem por Ordem (R$)", value=4.50)

# 3. Coleta de Dados Blindada
@st.cache_data(ttl=3600)
def get_safe_data(t, start, end):
    try:
        s = yf.Ticker(t)
        d = s.history(start=start, end=end)
        try: n = s.news
        except: n = []
        return d, n
    except:
        return pd.DataFrame(), []

df_acao, news = get_safe_data(ticker, data_compra, data_venda)

# 4. Validação e Renderização do Dashboard
if df_acao.empty or len(df_acao) < 2:
    st.warning("⚠️ Dados insuficientes para este período ou ativo. Tente mudar as datas na lateral.")
else:
    # Correção de Colunas MultiIndex
    if isinstance(df_acao.columns, pd.MultiIndex): 
        df_acao.columns = df_acao.columns.get_level_values(0)
    
    precos = df_acao['Close'].dropna()
    p_ini, p_fim = float(precos.iloc[0]), float(precos.iloc[-1])
    
    # Cálculos Financeiros Reais
    investido = p_ini * qtd
    valor_final_acao = p_fim * qtd
    dividendos_totais = df_acao['Dividends'].sum() * qtd
    
    lucro_prejuizo = (valor_final_acao - investido) + dividendos_totais - (taxa * 2)
    rentabilidade_final = (lucro_prejuizo / investido) * 100

    # Exibição das Métricas
    st.title(f"Dashboard de Investimentos: {busca}")
    col1, col2, col3 = st.columns(3)
    
    col1.metric("Total Investido", f"R$ {investido:,.2f}")
    col2.metric("Dividendos Recebidos", f"R$ {dividendos_totais:,.2f}")
    col3.metric("Resultado Líquido", f"R$ {lucro_prejuizo:,.2f}", delta=f"{rentabilidade_final:.2f}%")

    # Gráfico de Performance
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=precos.index, y=precos, name="Preço de Fechamento", line=dict(color='#34a853', width=2)))
    fig.update_layout(
        template="plotly_dark", 
        height=450, 
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(title="Período"),
        yaxis=dict(title="Preço (R$)")
    )
    st.plotly_chart(fig, use_container_width=True)

    # 5. IA GEMINI (Reparo do erro 404 e Fallback)
    st.divider()
    if st.button("✨ Gerar Insight com Gemini IA"):
        with st.spinner("IA analisando fundamentos e notícias..."):
            try:
                # Tentativa 1: Nome do modelo atualizado para evitar o erro 404
                model = genai.GenerativeModel('gemini-1.5-flash-latest')
                
                contexto_noticias = [n.get('title', 'Notícia sem título') for n in news[:3]] if news else ["Nenhuma notícia encontrada."]
                
                prompt = f"Analise o ativo {busca}. Rentabilidade no período: {rentabilidade_final:.2f}%. Notícias: {contexto_noticias}. Como um economista, explique brevemente o que causou esse desempenho."
                
                response = model.generate_content(prompt)
                st.info(response.text)
                
            except Exception as e:
                # Tentativa 2: Fallback para o modelo Pro caso o Flash ainda apresente problemas
                try:
                    model_backup = genai.GenerativeModel('gemini-pro')
                    response = model_backup.generate_content(prompt)
                    st.info(response.text)
                except:
                    st.error(f"Erro técnico na IA: {str(e)}. Verifique se sua chave API está ativa no Google AI Studio.")
