import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Simulador B3", layout="wide")

# Interface Lateral
st.sidebar.header("Configurações de Simulação")
ticker = st.sidebar.text_input("Ativo (Ex: PETR4, VALE3)", value="PETR4").upper()
data_inicio = st.sidebar.date_input("Data de Compra", value=datetime(2023, 1, 1))
data_fim = st.sidebar.date_input("Data de Venda", value=datetime.today())
qtd_acoes = st.sidebar.number_input("Quantidade de Ações", min_value=1, value=100)
corretagem = st.sidebar.number_input("Corretagem por Ordem (R$)", min_value=0.0, value=4.50)

# Função para carregar dados de forma robusta
@st.cache_data
def carregar_dados(ticket, inicio, fim):
    if not ticket.endswith(".SA"):
        ticket = f"{ticket}.SA"
    # Adicionamos auto_adjust=False para garantir que a coluna 'Adj Close' exista
    df = yf.download(ticket, start=inicio, end=fim, auto_adjust=False)
    return df

try:
    dados = carregar_dados(ticker, data_inicio, data_fim)
    
    if not dados.empty:
        # Tratamento para evitar erro de colunas MultiIndex (comum em versões novas do yfinance)
        if isinstance(dados.columns, pd.MultiIndex):
            dados.columns = dados.columns.get_level_values(0)
            
        # Pegando os preços de fechamento ajustado
        preco_compra = float(dados['Adj Close'].iloc[0])
        preco_venda = float(dados['Adj Close'].iloc[-1])
        
        # Cálculos Financeiros
        investimento_inicial = (preco_compra * qtd_acoes) + corretagem
        valor_venda_bruto = (preco_venda * qtd_acoes) - corretagem
        
        # Dividendos
        ticker_obj = yf.Ticker(f"{ticker}.SA" if not ticker.endswith(".SA") else ticker)
        dividendos_df = ticker_obj.dividends.loc[str(data_inicio):str(data_fim)]
        total_dividendos = float(dividendos_df.sum() * qtd_acoes)
        
        lucro_liquido = (valor_venda_bruto - investimento_inicial) + total_dividendos
        rentabilidade = (lucro_liquido / investimento_inicial) * 100

        # Dashboard
        st.title(f"Dashboard Quantitativo: {ticker}")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Investido", f"R$ {investimento_inicial:,.2f}")
        col2.metric("Dividendos no Período", f"R$ {total_dividendos:,.2f}")
        col3.metric("Lucro Líquido", f"R$ {lucro_liquido:,.2f}", f"{rentabilidade:.2f}%")

        # Gráfico
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dados.index, 
            y=dados['Adj Close'], 
            mode='lines', 
            name='Preço Ajustado',
            line=dict(color='#00ff88')
        ))
        fig.update_layout(
            template="plotly_dark",
            xaxis_title="Período",
            yaxis_title="Preço (R$)",
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("Nenhum dado encontrado para este ativo ou período.")

except Exception as e:
    st.error(f"Erro ao processar simulação: {e}")
