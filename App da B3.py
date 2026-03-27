import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Simulador Invest B3", layout="wide", initial_sidebar_state="expanded")

# Estilização básica
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Simulador de Investimentos B3")
st.caption("Dados reais extraídos diretamente do Yahoo Finance")

# Sidebar Interativa
with st.sidebar:
    st.header("⚙️ Configurações")
    ticker = st.text_input("Ticker da Ação", value="PETR4").upper()
    if not ticker.endswith(".SA"):
        ticker_final = f"{ticker}.SA"
    else:
        ticker_final = ticker
    
    col_data1, col_data2 = st.columns(2)
    with col_data1:
        inicio = st.date_input("Compra", value=pd.to_datetime("2023-01-01"))
    with col_data2:
        fim = st.date_input("Venda", value=pd.to_datetime("2023-12-31"))
        
    qtd = st.number_input("Quantidade", min_value=1, value=100)
    taxa = st.number_input("Corretagem (R$)", value=4.50)
    
    btn = st.button("🚀 Simular Agora", use_container_width=True)

if btn:
    with st.spinner('Processando dados históricos...'):
        df = yf.download(ticker_final, start=inicio, end=fim)
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty:
            st.error("❌ Ops! Não achei dados para esse ticker ou data. Tente VALE3 ou ITUB4.")
        else:
            # Cálculos
            p_compra = float(df['Close'].iloc[0])
            p_venda = float(df['Close'].iloc[-1])
            investido = p_compra * qtd
            final_bruto = p_venda * qtd
            lucro_bruto = final_bruto - investido
            custos = taxa * 2
            ir = max(0, lucro_bruto * 0.15) if lucro_bruto > 0 else 0
            liquido = lucro_bruto - custos - ir
            perc = (liquido / investido) * 100

            # Exibição Visual (Cards)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Valor Investido", f"R$ {investido:,.2f}")
            c2.metric("Valor Final", f"R$ {final_bruto:,.2f}")
            c3.metric("Lucro Líquido", f"R$ {liquido:,.2f}", delta=f"{perc:.2f}%")
            c4.metric("Impostos/Taxas", f"R$ {(ir+custos):,.2f}")

            # Gráfico Interativo
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Preço', line=dict(color='#2ecc71', width=3)))
            fig.update_layout(
                title=f"Histórico de Preços: {ticker_final}",
                hovermode="x unified",
                plot_bgcolor='white',
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.success(f"Simulação concluída! Se você tivesse comprado {qtd} ações de {ticker} em {inicio.strftime('%d/%m/%y')}, teria hoje R$ {liquido:,.2f} de lucro líquido.")