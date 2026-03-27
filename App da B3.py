import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Simulador B3", layout="wide")

# Estilização que se adapta ao tema (Claro/Escuro)
st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background-color: rgba(120, 120, 120, 0.1);
        padding: 20px;
        border-radius: 10px;
        border: 1px solid rgba(120, 120, 120, 0.2);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 Simulador de Investimentos B3")
st.caption("Simulação baseada em dados históricos reais do Yahoo Finance")

# Painel Lateral (Sidebar)
with st.sidebar:
    st.header("⚙️ Configurações")
    ticker_input = st.text_input("Ticker da Ação (ex: PETR4, VALE3)", "PETR4")
    ticker = ticker_input.strip().upper()
    if not ticker.endswith(".SA"):
        ticker = f"{ticker}.SA"
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        data_inicio = st.date_input("Data de Compra", pd.to_datetime("2023-01-01"))
    with col_d2:
        data_fim = st.date_input("Data de Venda", pd.to_datetime("2023-12-31"))
        
    quantidade = st.number_input("Quantidade de Ações", min_value=1, value=100)
    corretagem = st.number_input("Corretagem por Ordem (R$)", value=4.50)
    
    btn_simular = st.button("🚀 Simular Investimento", use_container_width=True)

# Lógica principal
if btn_simular:
    with st.spinner('Buscando dados na B3...'):
        df = yf.download(ticker, start=data_inicio, end=data_fim)
        
        # Ajuste para diferentes versões da biblioteca yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty:
            st.error(f"❌ Não encontramos dados para {ticker}. Verifique se o ticker está correto ou se as datas são válidas.")
        else:
            # Cálculos Financeiros
            p_compra = float(df['Close'].iloc[0])
            p_venda = float(df['Close'].iloc[-1])
            
            valor_investido = p_compra * quantidade
            valor_final_bruto = p_venda * quantidade
            lucro_bruto = valor_final_bruto - valor_investido
            
            custos_corretagem = corretagem * 2 # Compra e Venda
            imposto_renda = max(0, lucro_bruto * 0.15) if lucro_bruto > 0 else 0
            
            lucro_liquido = lucro_bruto - custos_corretagem - imposto_renda
            rentabilidade = (lucro_liquido / valor_investido) * 100

            # Exibição dos Indicadores (Metrics)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Valor Investido", f"R$ {valor_investido:,.2f}")
            c2.metric("Valor Final", f"R$ {valor_final_bruto:,.2f}")
            
            # Cor do delta (verde para lucro, vermelho para prejuízo)
            c3.metric("Lucro Líquido", f"R$ {lucro_liquido:,.2f}", delta=f"{rentabilidade:.2f}%")
            c4.metric("Custos (Taxas+IR)", f"R$ {(custos_corretagem + imposto_renda):,.2f}")

            # Gráfico de Preços Interativo
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df.index, 
                y=df['Close'], 
                name="Preço de Fechamento",
                line=dict(color='#00d1b2', width=2)
            ))
            
            fig.update_layout(
                title=f"Evolução do Preço: {ticker}",
                xaxis_title="Data",
                yaxis_title="Preço (R$)",
                hovermode="x unified",
                template="plotly_dark" if st.session_state.get('theme') == 'dark' else "plotly_white",
                height=450
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.info(f"💡 Dica: O preço de compra considerado foi R$ {p_compra:.2f} (em {df.index[0].strftime('%d/%m/%Y')}).")
