import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(page_title="Simulador B3", layout="wide")

# Interface Lateral (Sidebar)
st.sidebar.header("Configurações de Simulação")
ticker = st.sidebar.text_input("Ativo (Ex: PETR4, VALE3)", value="PETR4").upper()
data_inicio = st.sidebar.date_input("Data de Compra", value=datetime(2023, 1, 1))
data_fim = st.sidebar.date_input("Data de Venda", value=datetime.today())
qtd_acoes = st.sidebar.number_input("Quantidade de Ações", min_value=1, value=100)
corretagem = st.sidebar.number_input("Corretagem por Ordem (R$)", min_value=0.0, value=4.50)

# Função para buscar dados
@st.cache_data
def carregar_dados(ticket, inicio, fim):
    # Adicionamos um sufixo .SA se não estiver presente
    if not ticket.endswith(".SA"):
        ticket = f"{ticket}.SA"
    df = yf.download(ticket, start=inicio, end=fim)
    return df

try:
    # Carregamento de dados
    dados = carregar_dados(ticker, data_inicio, data_fim)
    
    if not dados.empty:
        # Cálculos Financeiros
        preco_compra = dados['Adj Close'].iloc[0]
        preco_venda = dados['Adj Close'].iloc[-1]
        
        investimento_inicial = (preco_compra * qtd_acoes) + corretagem
        valor_final = (preco_venda * qtd_acoes) - corretagem
        lucro_preço = valor_final - investimento_inicial
        
        # Simulação de Dividendos (Simplificada via yfinance)
        ticker_obj = yf.Ticker(f"{ticker}.SA" if not ticker.endswith(".SA") else ticker)
        dividendos_hist = ticker_obj.dividends.loc[data_inicio:data_fim]
        total_dividendos = dividendos_hist.sum() * qtd_acoes
        
        lucro_liquido = lucro_preço + total_dividendos
        rentabilidade = (lucro_liquido / investimento_inicial) * 100

        # Dashboard Principal
        st.title(f"Análise de Performance: {ticker}")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Investido", f"R$ {float(investimento_inicial):,.2f}")
        col2.metric("Dividendos Recebidos", f"R$ {float(total_dividendos):,.2f}")
        col3.metric("Resultado Líquido", f"R$ {float(lucro_liquido):,.2f}", f"{float(rentabilidade):.2f}%")

        # Gráfico de Evolução
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dados.index, y=dados['Adj Close'], mode='lines', name='Preço Ajustado', line=dict(color='#00ff88')))
        fig.update_layout(
            title="Histórico de Preço (Ajustado)",
            template="plotly_dark",
            xaxis_title="Período",
            yaxis_title="Preço (R$)",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("Ajuste as datas: o mercado pode estar fechado hoje ou o ativo é inválido.")

except Exception as e:
    st.error(f"Erro inesperado: {e}")
