import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Simulador B3", layout="wide")

# 1. FUNÇÃO DE MAPEAMENTO DE NOMES (Solução para sua dúvida)
def tratar_ticker(nome):
    nome = nome.upper().strip()
    # Dicionário de conversão manual para nomes comuns
    de_para = {
        "ITAU": "ITUB4",
        "ITAÚ": "ITUB4",
        "PETROBRAS": "PETR4",
        "PETROBRÁS": "PETR4",
        "VALE": "VALE3",
        "BANCO DO BRASIL": "BBAS3",
        "BB": "BBAS3",
        "BRADESCO": "BBDC4",
        "MAGALU": "MGLU3",
        "NUBANK": "ROXO34",
    }
    
    # Se o que o usuário digitou está no dicionário, troca pelo ticker
    ticker_final = de_para.get(nome, nome)
    
    # Garante o sufixo .SA para a B3
    if not ticker_final.endswith(".SA"):
        ticker_final = f"{ticker_final}.SA"
    return ticker_final

# Interface Lateral
st.sidebar.header("Configurações de Simulação")
input_usuario = st.sidebar.text_input("Ativo ou Nome (Ex: Itaú, PETR4)", value="PETR4")
ticker_corrigido = tratar_ticker(input_usuario) # Aplica a correção aqui

data_inicio = st.sidebar.date_input("Data de Compra", value=datetime(2023, 1, 1))
data_fim = st.sidebar.date_input("Data de Venda", value=datetime.today())
qtd_acoes = st.sidebar.number_input("Quantidade de Ações", min_value=1, value=100)
corretagem = st.sidebar.number_input("Corretagem por Ordem (R$)", min_value=0.0, value=4.50)

# Função para carregar dados
@st.cache_data
def carregar_dados(tk, inicio, fim):
    try:
        df = yf.download(tk, start=inicio, end=fim, auto_adjust=False)
        return df
    except:
        return pd.DataFrame()

try:
    dados = carregar_dados(ticker_corrigido, data_inicio, data_fim)
    
    if not dados.empty and len(dados) > 0:
        # Limpeza de colunas MultiIndex (evita o erro 'Adj Close')
        if isinstance(dados.columns, pd.MultiIndex):
            dados.columns = [col[0] if isinstance(col, tuple) else col for col in dados.columns]
            
        # Cálculos com verificação de segurança
        if 'Adj Close' in dados.columns:
            preco_compra = float(dados['Adj Close'].iloc[0])
            preco_venda = float(dados['Adj Close'].iloc[-1])
            
            investimento_inicial = (preco_compra * qtd_acoes) + corretagem
            valor_venda_bruto = (preco_venda * qtd_acoes) - corretagem
            
            # Dividendos
            ticker_obj = yf.Ticker(ticker_corrigido)
            dividendos_df = ticker_obj.dividends.loc[str(data_inicio):str(data_fim)]
            total_dividendos = float(dividendos_df.sum() * qtd_acoes)
            
            lucro_liquido = (valor_venda_bruto - investimento_inicial) + total_dividendos
            rentabilidade = (lucro_liquido / investimento_inicial) * 100

            # Dashboard
            st.title(f"Resultado da Simulação: {ticker_corrigido.replace('.SA', '')}")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Investido", f"R$ {investimento_inicial:,.2f}")
            col2.metric("Dividendos", f"R$ {total_dividendos:,.2f}")
            col3.metric("Lucro Líquido", f"R$ {lucro_liquido:,.2f}", f"{rentabilidade:.2f}%")

            # Gráfico
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=dados.index, y=dados['Adj Close'], mode='lines', line=dict(color='#00ff88')))
            fig.update_layout(template="plotly_dark", title="Evolução do Preço Ajustado")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Coluna 'Adj Close' não encontrada. Tente outro ativo.")
    else:
        st.warning(f"Não encontramos dados para '{input_usuario}'. Verifique se o nome ou código está correto.")

except Exception as e:
    st.error(f"Erro na simulação: {e}")
