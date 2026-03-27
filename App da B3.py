import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. Configurações de Página
st.set_page_config(page_title="Simulador B3", layout="wide", initial_sidebar_state="expanded")

# 2. Template Moderno e Limpo (Sem Emojis, Estilo Premium)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0e1113; color: #ffffff; }
    
    /* Metrics Style */
    [data-testid="stMetric"] {
        background-color: #161a1d;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #2d3239;
    }
    [data-testid="stMetricLabel"] { color: #8a949e; font-weight: 400; }
    
    /* Inputs */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background-color: #1c2127 !important;
        border: 1px solid #30363d !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Banco de Dados Auxiliar para o Buscador (Nome -> Ticker)
banco_acoes = {
    "PETROBRAS": "PETR4", "VALE": "VALE3", "ITAU": "ITUB4", "BRADESCO": "BBDC4",
    "BANCO DO BRASIL": "BBAS3", "MAGAZINE LUIZA": "MGLU3", "MAGALU": "MGLU3",
    "AMBEV": "ABEV3", "WEG": "WEGE3", "NUBANK": "ROXO34", "B3": "B3SA3",
    "PETRO RIO": "PRIO3", "GERDAU": "GGBR4", "ELETROBRAS": "ELET3"
}

# 4. Sidebar: Data de Compra e Venda Sempre Visíveis
with st.sidebar:
    st.title("Parâmetros")
    
    # Buscador Inteligente
    busca = st.text_input("Buscar Ação (Nome ou Código)", "PETR4").strip().upper()
    
    # Lógica de sugestão
    ticker_sugerido = busca
    for nome, tick in banco_acoes.items():
        if busca in nome:
            ticker_sugerido = tick
            st.caption(f"Sugestão encontrada: {nome} ({tick})")
            break
            
    ticker = f"{ticker_sugerido}.SA" if not ticker_sugerido.endswith(".SA") else ticker_sugerido
    
    st.divider()
    
    # Datas sempre na esquerda (Padrão BR)
    data_compra = st.date_input("Data de Compra", value=pd.to_datetime("2023-01-01"), format="DD/MM/YYYY")
    data_venda = st.date_input("Data de Venda", value=datetime.now(), format="DD/MM/YYYY")
    
    st.divider()
    
    qtd = st.number_input("Quantidade de Ações", min_value=1, value=100)
    taxa = st.number_input("Corretagem (R$)", value=0.0, step=0.5)

# 5. Lógica de Dados
df = yf.download(ticker, start=data_compra, end=data_venda, progress=False)
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

if not df.empty:
    st.title(f"Relatório de Performance: {ticker_sugerido}")
    
    # Cálculos
    p_ini, p_fim = float(df['Close'].iloc[0]), float(df['Close'].iloc[-1])
    inv = p_ini * qtd
    bruto = p_fim * qtd
    lucro_b = bruto - inv
    custos = taxa * 2
    ir = max(0, lucro_b * 0.15) if lucro_b > 0 else 0
    liq = lucro_b - custos - ir
    rent = (liq / inv) * 100

    # Dashboard
    c1, c2, c3, c4 = st.columns(4)
    def fmt(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    c1.metric("Investido", fmt(inv))
    c2.metric("Valor Final", fmt(bruto))
    c3.metric("Lucro Líquido", fmt(liq), delta=f"{rent:.2f}%")
    c4.metric("Custos Totais", fmt(ir+custos))

    # 6. Gráfico Estilo Google (Sem zoom de mouse, com botões de controle)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'],
        line=dict(color='#34a853' if liq >= 0 else '#ea4335', width=2),
        fill='tozeroy', fillcolor='rgba(52, 168, 83, 0.05)',
        hovertemplate='<b>%{y:.2f} BRL</b><extra></extra>'
    ))

    fig.update_layout(
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=20, b=0),
        hovermode="x unified",
        xaxis=dict(
            showgrid=False, tickformat="%d/%m/%y",
            fixedrange=True # DESATIVA O ZOOM DO MOUSE/ARRASTE
        ),
        yaxis=dict(
            side="right", gridcolor='#2d3239', tickprefix="R$ ",
            fixedrange=True # DESATIVA O ZOOM NO EIXO Y
        ),
        height=500
    )

    # Exibe o gráfico com os botões de expandir e barra de ferramentas limitada
    st.plotly_chart(fig, use_container_width=True, config={
        'displaylogo': False,
        'modeBarButtonsToAdd': ['zoomIn2d', 'zoomOut2d', 'fullscreen'], # Botões específicos que você pediu
        'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'autoScale2d'], # Tira o "arrastar"
        'displayModeBar': True # Deixa a barra visível para você usar os botões de +/-
    })
    
    st.caption(f"Preço de compra: R$ {p_ini:.2f} | Preço de venda: R$ {p_fim:.2f}")

else:
    st.error("Não foi possível carregar dados. Verifique o ticker e o período.")
