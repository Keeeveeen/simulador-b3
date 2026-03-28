import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Simulador B3 - Pro", layout="wide")

# 1. TRADUTOR DE NOMES PARA TICKERS
def tratar_ticker(nome):
    nome = nome.upper().strip()
    de_para = {
        "ITAU": "ITUB4", "ITAÚ": "ITUB4", "SANTANDER": "SANB11", 
        "INTER": "INTR", "BANCO INTER": "INTR", "BRADESCO": "BBDC4",
        "BANCO DO BRASIL": "BBAS3", "BB": "BBAS3", "NUBANK": "ROXO34",
        "BTG": "BPAC11", "XP": "XPBR31", "ITAUSA": "ITSA4", "ITAÚSA": "ITSA4",
        "MAGALU": "MGLU3", "MAGAZINE LUIZA": "MGLU3", "CASAS BAHIA": "BHIA3",
        "PETROBRAS": "PETR4", "PETROBRÁS": "PETR4", "VALE": "VALE3",
        "WEG": "WEGE3", "SUZANO": "SUZB3", "GERDAU": "GGBR4",
        "ELETROBRAS": "ELET3", "ELETROBRÁS": "ELET3", "TAESA": "TAEE11"
    }
    ticker_final = de_para.get(nome, nome)
    internacionais = ["INTR", "MELI34", "XPBR31", "ROXO34"]
    if ticker_final not in internacionais and not ticker_final.endswith(".SA"):
        ticker_final = f"{ticker_final}.SA"
    return ticker_final

# 2. INTERFACE LATERAL
st.sidebar.header("📊 Configurações")
input_usuario = st.sidebar.text_input("Ativo ou Empresa", value="PETR4")
ticker_busca = tratar_ticker(input_usuario)

data_inicio = st.sidebar.date_input("Data de Compra", value=datetime(2023, 1, 1))
data_fim = st.sidebar.date_input("Data de Venda", value=datetime.today())
qtd_acoes = st.sidebar.number_input("Quantidade de Ações", min_value=1, value=100)
corretagem = st.sidebar.number_input("Corretagem por Ordem (R$)", min_value=0.0, value=4.50)

# 3. FUNÇÃO DE DADOS
@st.cache_data
def buscar_dados(tk, inicio, fim):
    try:
        df = yf.download(tk, start=inicio, end=fim, auto_adjust=False)
        return df
    except:
        return pd.DataFrame()

# 4. EXECUÇÃO PRINCIPAL (Bloco Try/Except Completo)
try:
    df_precos = buscar_dados(ticker_busca, data_inicio, data_fim)
    
    if not df_precos.empty:
        # Resolve erro 'Adj Close' de MultiIndex
        if isinstance(df_precos.columns, pd.MultiIndex):
            df_precos.columns = [col[0] if isinstance(col, tuple) else col for col in df_precos.columns]
        
        coluna_alvo = 'Adj Close' if 'Adj Close' in df_precos.columns else 'Close'
        
        p_compra = float(df_precos[coluna_alvo].iloc[0])
        p_venda = float(df_precos[coluna_alvo].iloc[-1])
        
        investido = (p_compra * qtd_acoes) + corretagem
        venda_bruta = (p_venda * qtd_acoes) - corretagem
        
        obj_ticker = yf.Ticker(ticker_busca)
        divs = obj_ticker.dividends.loc[str(data_inicio):str(data_fim)]
        total_divs = float(divs.sum() * qtd_acoes)
        
        lucro_abs = (venda_bruta - investido) + total_divs
        rentab_pct = (lucro_abs / investido) * 100

        st.title(f"Resultado: {ticker_busca.replace('.SA', '')}")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Investimento Total", f"R$ {investido:,.2f}")
        m2.metric("Dividendos", f"R$ {total_divs:,.2f}")
        m3.metric("Lucro Líquido", f"R$ {lucro_abs:,.2f}", f"{rentab_pct:.2f}%")

        # Gráfico
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_precos.index, y=df_precos[coluna_alvo], mode='lines', line=dict(color='#00ff88')))
        fig.update_layout(template="plotly_dark", title=f"Evolução {ticker_busca}")
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning(f"Não foram encontrados dados para '{input_usuario}'.")

except Exception as e:
    st.error(f"Erro na simulação: {e}")
