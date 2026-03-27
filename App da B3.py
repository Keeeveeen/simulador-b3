import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# 1. Configurações de Página e Estilo
st.set_page_config(page_title="Simulador B3 Ultra", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0e1113; color: #ffffff; }
    [data-testid="stMetric"] {
        background-color: #161a1d;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #2d3239;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. Buscador Inteligente Expandido
banco_acoes = {
    "PETROBRAS": "PETR4", "VALE": "VALE3", "ITAU": "ITUB4", "BRADESCO": "BBDC4",
    "BANCO DO BRASIL": "BBAS3", "MAGALU": "MGLU3", "AMBEV": "ABEV3", "WEG": "WEGE3",
    "NUBANK": "ROXO34", "B3": "B3SA3", "PRIO": "PRIO3", "GERDAU": "GGBR4",
    "ELETROBRAS": "ELET3", "SANTANDER": "SANB11", "BTG": "BPAC11"
}

with st.sidebar:
    st.title("Parâmetros Profissionais")
    busca = st.text_input("Ativo (Nome ou Código)", "PETR4").strip().upper()
    
    # Lógica de Busca Fuzzy Simples
    ticker_sugerido = busca
    for nome, tick in banco_acoes.items():
        if busca in nome or busca == tick:
            ticker_sugerido = tick
            st.caption(f"Ativo selecionado: {nome} ({tick})")
            break
            
    ticker = f"{ticker_sugerido}.SA" if not ticker_sugerido.endswith(".SA") else ticker_sugerido
    
    st.divider()
    data_compra = st.date_input("Início da Simulação", value=pd.to_datetime("2023-01-01"), format="DD/MM/YYYY")
    data_venda = st.date_input("Fim da Simulação", value=datetime.now(), format="DD/MM/YYYY")
    
    st.divider()
    qtd = st.number_input("Quantidade", min_value=1, value=100)
    taxa = st.number_input("Corretagem Fixa (R$)", value=0.0)
    selic_anual = st.number_input("Taxa Livre de Risco (% aa)", value=10.75) # Para o Sharpe

# 3. Coleta de Dados (Ação + Ibovespa + Dividendos)
@st.cache_data(ttl=3600)
def carregar_dados(ticker, start, end):
    # Puxa dados da ação com ações (dividendos/splits)
    data = yf.Ticker(ticker)
    df = data.history(start=start, end=end)
    
    # Puxa Ibovespa para comparação
    ibov = yf.download("^BVSP", start=start, end=end, progress=False)['Close']
    return df, ibov

try:
    df, ibov = carregar_dados(ticker, data_compra, data_venda)

    if not df.empty:
        # --- CÁLCULOS AVANÇADOS ---
        # 1. Dividendos no período
        total_dividendos = df['Dividends'].sum() * qtd
        
        # 2. Performance da Ação
        p_ini, p_fim = float(df['Close'].iloc[0]), float(df['Close'].iloc[-1])
        investido = p_ini * qtd
        bruto_capital = p_fim * qtd
        lucro_cap = bruto_capital - investido
        
        # 3. Impostos e Taxas
        custos_operacionais = taxa * 2
        imposto = max(0, lucro_cap * 0.15) if lucro_cap > 0 else 0
        
        # Resultado Final (Capital + Dividendos - Custos)
        resultado_liquido = lucro_cap + total_dividendos - custos_operacionais - imposto
        rentabilidade_total = (resultado_liquido / investido) * 100
        
        # 4. Benchmarking (Ibovespa)
        ibov_ini, ibov_fim = float(ibov.iloc[0]), float(ibov.iloc[-1])
        rent_ibov = ((ibov_fim / ibov_ini) - 1) * 100
        alpha = rentabilidade_total - rent_ibov # O quanto você bateu o mercado
        
        # 5. Volatilidade e Sharpe (Risco)
        retornos_diarios = df['Close'].pct_change().dropna()
        vol_anual = retornos_diarios.std() * np.sqrt(252) * 100
        taxa_diaria_livre_risco = (1 + (selic_anual/100))**(1/252) - 1
        excesso_retorno = retornos_diarios.mean() - taxa_diaria_livre_risco
        sharpe = (excesso_retorno / retornos_diarios.std()) * np.sqrt(252) if retornos_diarios.std() != 0 else 0

        # --- INTERFACE ---
        st.title(f"Análise de Performance: {ticker_sugerido}")
        
        # Linha 1: Financeiro
        c1, c2, c3, c4 = st.columns(4)
        def fmt(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        c1.metric("Investimento Inicial", fmt(investido))
        c2.metric("Dividendos Recebidos", fmt(total_dividendos))
        c3.metric("Resultado Líquido", fmt(resultado_liquido), delta=f"{rentabilidade_total:.2f}%")
        c4.metric("Alpha (vs Ibov)", f"{alpha:+.2f}%", delta_color="normal")

        # Linha 2: Risco e Benchmark
        st.divider()
        r1, r2, r3 = st.columns(3)
        r1.metric("Volatilidade Anualizada", f"{vol_anual:.2f}%")
        r2.metric("Índice Sharpe", f"{sharpe:.2f}")
        r3.metric("Retorno Ibovespa", f"{rent_ibov:.2f}%")

        # --- GRÁFICO COMPARATIVO ---
        # Normalizando para base 100 para comparação justa
        acao_norm = (df['Close'] / p_ini) * 100
        ibov_norm = (ibov / ibov_ini) * 100

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=acao_norm, name=ticker_sugerido, line=dict(color='#34a853', width=2.5)))
        fig.add_trace(go.Scatter(x=ibov.index, y=ibov_norm, name="IBOVESPA", line=dict(color='#8a949e', width=1.5, dash='dot')))

        fig.update_layout(
            template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=20, b=0), hovermode="x unified",
            xaxis=dict(showgrid=False, tickformat="%d/%m/%y", fixedrange=True),
            yaxis=dict(side="right", gridcolor='#2d3239', ticksuffix="%", title="Base 100", fixedrange=True),
            height=500, showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'modeBarButtonsToAdd': ['fullscreen']})
        
        st.info(f"O Índice Sharpe de **{sharpe:.2f}** indica o quanto de retorno você teve para cada unidade de risco. Acima de 1.0 é considerado ótimo.")

except Exception as e:
    st.error(f"Erro ao processar simulação. Verifique os dados. Detalhe: {e}")
