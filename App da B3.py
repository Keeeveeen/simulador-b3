import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configurações iniciais da página
st.set_page_config(page_title="Simulador B3 Pro", layout="wide")

# Estilização Minimalista e Moderna
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    [data-testid="stMetric"] {
        background-color: rgba(28, 131, 225, 0.03);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid rgba(28, 131, 225, 0.1);
    }
    .stButton>button {
        border-radius: 8px;
        background-color: #1c83e1;
        color: white;
        font-weight: 600;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# Título Limpo
st.title("📈 Simulador de Trading Histórico")
st.caption("Performance baseada em dados reais da B3")

# Sidebar - Parâmetros de Entrada
with st.sidebar:
    st.header("Configurações")
    ticker_raw = st.text_input("Ação (ex: VALE3, PETR4)", "PETR4").strip().upper()
    ticker = f"{ticker_raw}.SA" if not ticker_raw.endswith(".SA") else ticker_raw
    
    quantidade = st.number_input("Quantidade de Ações", min_value=1, value=100, step=10)
    corretagem = st.number_input("Corretagem (R$)", value=0.00, step=0.50)
    
    st.divider()
    
    # Seleção de Período estilo "Google"
    periodo = st.selectbox("Período Rápido", 
                         ["Personalizado", "1 Mês", "6 Meses", "1 Ano", "5 Anos"], 
                         index=3)
    
    hoje = datetime.now()
    if periodo == "1 Mês":
        data_inicio = hoje - timedelta(days=30)
        data_fim = hoje
    elif periodo == "6 Meses":
        data_inicio = hoje - timedelta(days=180)
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
            data_inicio = st.date_input("Início", value=pd.to_datetime("2023-01-01"), format="DD/MM/YYYY")
        with col_d2:
            data_fim = st.date_input("Fim", value=pd.to_datetime("2023-12-31"), format="DD/MM/YYYY")

# Lógica de Dados
df = yf.download(ticker, start=data_inicio, end=data_fim, progress=False)

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

    # Dashboard de Métricas - Valores Formatados (2 casas decimais)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Investido", f"R$ {investido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("Valor Final", f"R$ {final_bruto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    cor_lucro = "normal" if liquido >= 0 else "inverse"
    c3.metric("Lucro Líquido", f"R$ {liquido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), 
              delta=f"{rentabilidade:.2f}%", delta_color=cor_lucro)
    
    c4.metric("Impostos/Taxas", f"R$ {(ir+custos):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # Gráfico Estilo Google (Interativo)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['Close'], 
        name="Preço",
        line=dict(color='#1c83e1', width=2),
        fill='tozeroy',
        fillcolor='rgba(28, 131, 225, 0.1)' # Efeito de sombra azul claro
    ))

    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor='white',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(
            showgrid=False, 
            title="", 
            tickformat="%d/%m/%y" # Data formato BR no eixo X
        ),
        yaxis=dict(
            side="right", 
            gridcolor='rgba(0,0,0,0.05)', 
            title="",
            tickprefix="R$ "
        ),
        height=500,
        dragmode='pan'
    )

    st.plotly_chart(fig, use_container_width=True)
    
    # Detalhes da operação em formato BR
    st.write(f"ℹ️ Compra realizada em: **{df.index[0].strftime('%d/%m/%Y')}** | Venda em: **{df.index[-1].strftime('%d/%m/%Y')}**")

else:
    st.warning("⚠️ Selecione um período ou ticker válido para ver os dados.")
