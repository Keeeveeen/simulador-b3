import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configurações iniciais da página (Tema Escuro como Padrão)
st.set_page_config(page_title="Simulador B3 Pro", layout="wide", initial_sidebar_state="collapsed")

# Estilização Minimalista (Modo Escuro Forçado)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500&display=swap');
    
    /* Fonte estilo Google */
    html, body, [class*="css"], .stText { font-family: 'Roboto', sans-serif; }
    
    /* Fundo Escuro */
    .stApp { background-color: #101214; color: #e8eaed; }
    
    /* Estilo dos Cards (Métricas) */
    [data-testid="stMetric"] {
        background-color: #1a1c1e;
        padding: 25px;
        border-radius: 8px;
        border: 1px solid #2d3033;
    }
    [data-testid="stMetricLabel"] { color: #9aa0a6; font-size: 14px; }
    [data-testid="stMetricValue"] { color: #e8eaed; font-size: 28px; font-weight: 400; }
    
    /* Botão Lateral */
    .stButton>button {
        border-radius: 4px;
        background-color: #303134;
        color: #e8eaed;
        font-weight: 500;
        border: 1px solid #5f6368;
    }
    
    /* Remove Emojis e limpa cabeçalho */
    .css-10trblm { font-size: 24px; }
    </style>
    """, unsafe_allow_html=True)

# Título Limpo (Sem Emojis)
st.title("Simulador de Trading Histórico")
st.caption("Performance baseada em dados reais da B3 extraídos do Yahoo Finance")

# Sidebar - Parâmetros de Entrada
with st.sidebar:
    st.header("Configurações")
    ticker_raw = st.text_input("Ação (ex: VALE3, PETR4)", "PETR4").strip().upper()
    ticker = f"{ticker_raw}.SA" if not ticker_raw.endswith(".SA") else ticker_raw
    
    quantidade = st.number_input("Quantidade de Ações", min_value=1, value=100, step=10)
    corretagem = st.number_input("Corretagem por Ordem (R$)", value=0.00, step=0.50)
    
    st.divider()
    
    # Seleção de Período estilo "Google"
    periodo = st.selectbox("Período Rápido", 
                         ["Personalizado", "1 Mês", "6 Meses", "YTD", "1 Ano", "5 Anos"], 
                         index=4)
    
    hoje = datetime.now()
    if periodo == "1 Mês":
        data_inicio = hoje - timedelta(days=30)
        data_fim = hoje
    elif periodo == "6 Meses":
        data_inicio = hoje - timedelta(days=180)
        data_fim = hoje
    elif periodo == "YTD":
        data_inicio = datetime(hoje.year, 1, 1)
        data_fim = hoje
    elif periodo == "1 Ano":
        data_inicio = hoje - timedelta(days=365)
        data_fim = hoje
    elif periodo == "5 Anos":
        data_inicio = hoje - timedelta(days=365*5)
        data_fim = hoje
    else:
        # Padrão Data BR no seletor
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            data_inicio = st.date_input("Início", value=pd.to_datetime("2021-03-29"), format="DD/MM/YYYY")
        with col_d2:
            data_fim = st.date_input("Fim", value=pd.to_datetime("2026-03-26"), format="DD/MM/YYYY")

# Lógica de Dados
df = yf.download(ticker, start=data_inicio, end=data_fim, progress=False)

# Correção de MultiIndex do yfinance
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

if not df.empty:
    # Cálculos
    p_compra = float(df['Close'].iloc[0])
    p_venda = float(df['Close'].iloc[-1])
    
    investido = p_compra * quantidade
    final_bruto = p_venda * quantidade
    lucro_bruto = final_bruto - investido
    custos = corretagem * 2
    ir = max(0, lucro_bruto * 0.15) if lucro_bruto > 0 else 0
    liquido = lucro_bruto - custos - ir
    rentabilidade = (liquido / investido) * 100

    # Dashboard de Métricas - Valores Formatados (2 casas decimais, padrão BR)
    c1, c2, c3, c4 = st.columns(4)
    
    def formatar_br(valor):
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    c1.metric("Investido", formatar_br(investido))
    c2.metric("Valor Final", formatar_br(final_bruto))
    
    # Delta (Rentabilidade) sem emoji, apenas porcentagem
    c3.metric("Lucro Líquido", formatar_br(liquido), 
              delta=f"{rentabilidade:.2f}%", delta_color="normal")
    
    c4.metric("Impostos/Taxas", formatar_br(ir+custos))

    st.divider()

    # Gráfico ESTILO GOOGLE (Clean, Linha Verde, Fundo Escuro)
    fig = go.Figure()
    
    # Trace principal (Linha e Preenchimento)
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['Close'], 
        name="Preço",
        mode='lines',
        line=dict(color='#34a853', width=2), # Verde Google
        fill='tozeroy',
        fillcolor='rgba(52, 168, 83, 0.08)', # Preenchimento verde muito suave
        
        # Correção do Bug do Hover: Força apenas 2 casas decimais no hover
        hovertemplate='<b>%{y:.2f} BRL</b><extra></extra>' 
    ))

    # Configuração do Layout do Gráfico (Idêntico ao Google)
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0),
        
        # Hover unificado e limpo
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#202124", font_size=12, font_family="Roboto"),
        
        # Eixo X (Datas BR)
        xaxis=dict(
            showgrid=False, 
            title="", 
            tickformat="%d/%m/%y", # Data BR
            tickfont=dict(color="#9aa0a6", size=10),
            linecolor='#3c4043'
        ),
        
        # Eixo Y (Preços na Direita)
        yaxis=dict(
            side="right", 
            showgrid=True,
            gridcolor='#2d3033', # Linhas de grade sutis
            title="",
            tickprefix="R$ ",
            tickfont=dict(color="#9aa0a6", size=10),
            zeroline=False
        ),
        height=400,
        dragmode='pan'
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}) # Remove barra de ferramentas irritante
    
    # Detalhes da operação em formato BR (Sem Emojis)
    st.caption(f"Compra realizada em: {df.index[0].strftime('%d/%m/%Y')} | Venda em: {df.index[-1].strftime('%d/%m/%Y')}")

else:
    st.warning("Selecione um período ou ticker válido para ver os dados.")
