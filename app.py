import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Simulador B3 - Pro", layout="wide")

# 1. TRADUTOR DE NOMES PARA TICKERS (Buscador Inteligente)
def tratar_ticker(nome):
    nome = nome.upper().strip()
    
    # Dicionário manual para nomes comuns que o yfinance não entende direto
    de_para = {
        # Bancos e Financeiro
        "ITAU": "ITUB4", "ITAÚ": "ITUB4", "SANTANDER": "SANB11", 
        "INTER": "INTR", "BANCO INTER": "INTR", "BRADESCO": "BBDC4",
        "BANCO DO BRASIL": "BBAS3", "BB": "BBAS3", "NUBANK": "ROXO34",
        "BTG": "BPAC11", "XP": "XPBR31", "ITAUSA": "ITSA4", "ITAÚSA": "ITSA4",

        # Varejo e Consumo
        "MAGALU": "MGLU3", "MAGAZINE LUIZA": "MGLU3", "CASAS BAHIA": "BHIA3",
        "VIA VAREJO": "BHIA3", "LOJAS RENNER": "LREN3", "RENNER": "LREN3",
        "AREZZO": "ARZZ3", "MERCADO LIVRE": "MELI34", "AMBEV": "ABEV3",

        # Commodities, Energia e Indústria
        "PETROBRAS": "PETR4", "PETROBRÁS": "PETR4", "VALE": "VALE3",
        "WEG": "WEGE3", "SUZANO": "SUZB3", "GERDAU": "GGBR4",
        "ELETROBRAS": "ELET3", "ELETROBRÁS": "ELET3", "EQUATORIAL": "EQTL3",
        "TAESA": "TAEE11", "ENGIE": "EGIE3",

        # Outros Populares
        "AZUL": "AZUL4", "GOL": "GOLL4", "LOCALIZA": "RENT3", "HAPVIDA": "HAPV3",
        "B3": "B3SA3"
    }
    
    # Tenta traduzir o nome, se não achar, usa o que foi digitado
    ticker_final = de_para.get(nome, nome)
    
    # Regra para ativos da B3 (adiciona .SA se não tiver e não for ativo internacional como INTR ou MELI34)
    ativos_internacionais = ["INTR", "MELI34", "XPBR31", "ROXO34"]
    
    if ticker_final not in ativos_internacionais and not ticker_final.endswith(".SA"):
        ticker_final = f"{ticker_final}.SA"
        
    return ticker_final

# 2. INTERFACE LATERAL (Sidebar)
st.sidebar.header("📊 Configurações")
input_usuario = st.sidebar.text_input("Ativo ou Empresa (Ex: Itaú, PETR4)", value="PETR4")
ticker_busca = tratar_ticker(input_usuario)

data_inicio = st.sidebar.date_input("Data de Compra", value=datetime(2023, 1, 1))
data_fim = st.sidebar.date_input("Data de Venda", value=datetime.today())
qtd_acoes = st.sidebar.number_input("Quantidade de Ações", min_value=1, value=100)
corretagem = st.sidebar.number_input("Corretagem por Ordem (R$)", min_value=0.0, value=4.50)

# 3. LÓGICA DE DADOS
@st.cache_data
