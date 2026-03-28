import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(
    page_title="WealthMaster Pro - Plataforma Avançada de Investimentos",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem;
    }
    .warning-text {
        color: #ff6b6b;
        font-weight: bold;
    }
    .success-text {
        color: #51cf66;
        font-weight: bold;
    }
    .info-box {
        background-color: #1e1e1e;
        padding: 1rem;
        border-left: 4px solid #667eea;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ==================== FUNÇÕES DE INDICADORES TÉCNICOS MANUAIS ====================

def calculate_sma(data, window):
    """Calcula Média Móvel Simples"""
    return data.rolling(window=window).mean()

def calculate_ema(data, window):
    """Calcula Média Móvel Exponencial"""
    return data.ewm(span=window, adjust=False).mean()

def calculate_rsi(data, window=14):
    """Calcula RSI (Relative Strength Index)"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data, fast=12, slow=26, signal=9):
    """Calcula MACD"""
    ema_fast = calculate_ema(data, fast)
    ema_slow = calculate_ema(data, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(data, window=20, num_std=2):
    """Calcula Bandas de Bollinger"""
    sma = calculate_sma(data, window)
    std = data.rolling(window=window).std()
    upper_band = sma + (std * num_std)
    lower_band = sma - (std * num_std)
    return upper_band, sma, lower_band

def calculate_stochastic(high, low, close, k_window=14, d_window=3):
    """Calcula Oscilador Estocástico"""
    lowest_low = low.rolling(window=k_window).min()
    highest_high = high.rolling(window=k_window).max()
    k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d = k.rolling(window=d_window).mean()
    return k, d

def calculate_atr(high, low, close, window=14):
    """Calcula Average True Range"""
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=window).mean()
    return atr

def calculate_obv(close, volume):
    """Calcula On-Balance Volume"""
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    return obv

# ==================== CLASSE PRINCIPAL ====================

class WealthAnalyzer:
    """Classe principal para análise de investimentos"""
    
    def __init__(self, ticker, start_date, end_date):
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date
        self.data = None
        self.load_data()
    
    def load_data(self):
        """Carrega dados do ativo"""
        try:
            self.data = yf.download(self.ticker, start=self.start_date, end=self.end_date, progress=False)
            if not self.data.empty:
                if isinstance(self.data.columns, pd.MultiIndex):
                    self.data.columns = [col[0] if isinstance(col, tuple) else col for col in self.data.columns]
                self.calculate_indicators()
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
    
    def calculate_indicators(self):
        """Calcula indicadores técnicos"""
        close = self.data['Close'] if 'Close' in self.data.columns else self.data['Adj Close']
        high = self.data['High']
        low = self.data['Low']
        volume = self.data['Volume'] if 'Volume' in self.data.columns else pd.Series(index=self.data.index)
        
        # Médias Móveis
        self.data['SMA_20'] = calculate_sma(close, 20)
        self.data['SMA_50'] = calculate_sma(close, 50)
        self.data['EMA_12'] = calculate_ema(close, 12)
        self.data['EMA_26'] = calculate_ema(close, 26)
        
        # MACD
        macd, signal, hist = calculate_macd(close)
        self.data['MACD'] = macd
        self.data['MACD_Signal'] = signal
        self.data['MACD_Hist'] = hist
        
        # RSI
        self.data['RSI'] = calculate_rsi(close)
        
        # Bandas de Bollinger
        upper, middle, lower = calculate_bollinger_bands(close)
        self.data['BB_Upper'] = upper
        self.data['BB_Middle'] = middle
        self.data['BB_Lower'] = lower
        
        # Stochastic
        k, d = calculate_stochastic(high, low, close)
        self.data['Stoch_K'] = k
        self.data['Stoch_D'] = d
        
        # ATR
        self.data['ATR'] = calculate_atr(high, low, close)
        
        # OBV
        if 'Volume' in self.data.columns:
            self.data['OBV'] = calculate_obv(close, volume)
    
    def get_technical_signals(self):
        """Gera sinais técnicos combinados"""
        signals = []
        last_row = self.data.iloc[-1]
        prev_row = self.data.iloc[-2]
        
        # RSI
        if last_row['RSI'] < 30:
            signals.append(("📈 RSI", "Sobrevendido (Sinal de Compra)", "success-text"))
        elif last_row['RSI'] > 70:
            signals.append(("📉 RSI", "Sobrecomprado (Sinal de Venda)", "warning-text"))
        else:
            signals.append(("⚖️ RSI", f"Neutro ({last_row['RSI']:.1f})", "info-text"))
        
        # MACD
        if last_row['MACD'] > last_row['MACD_Signal'] and prev_row['MACD'] <= prev_row['MACD_Signal']:
            signals.append(("🟢 MACD", "Cruzamento de Alta", "success-text"))
        elif last_row['MACD'] < last_row['MACD_Signal'] and prev_row['MACD'] >= prev_row['MACD_Signal']:
            signals.append(("🔴 MACD", "Cruzamento de Baixa", "warning-text"))
        else:
            signals.append(("⚖️ MACD", "Neutro", "info-text"))
        
        # Bandas de Bollinger
        close = last_row['Close'] if 'Close' in last_row.index else last_row['Adj Close']
        if close <= last_row['BB_Lower']:
            signals.append(("📊 Bollinger", "Preço na banda inferior (Potencial Compra)", "success-text"))
        elif close >= last_row['BB_Upper']:
            signals.append(("📊 Bollinger", "Preço na banda superior (Potencial Venda)", "warning-text"))
        else:
            signals.append(("⚖️ Bollinger", "Preço na faixa neutra", "info-text"))
        
        # Stochastic
        if last_row['Stoch_K'] < 20 and last_row['Stoch_D'] < 20:
            signals.append(("🎯 Stochastic", "Sobrevendido (Sinal de Compra)", "success-text"))
        elif last_row['Stoch_K'] > 80 and last_row['Stoch_D'] > 80:
            signals.append(("🎯 Stochastic", "Sobrecomprado (Sinal de Venda)", "warning-text"))
        
        return signals
    
    def calculate_risk_metrics(self):
        """Calcula métricas de risco"""
        returns = self.data['Close'].pct_change().dropna()
        
        # Volatilidade anualizada
        volatility = returns.std() * np.sqrt(252)
        
        # Sharpe Ratio (assumindo taxa livre de risco de 0%)
        sharpe = (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        
        # Drawdown máximo
        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # VaR 95%
        var_95 = np.percentile(returns, 5)
        
        # CVaR 95%
        cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else var_95
        
        metrics = {
            'Volatilidade (Anual)': f"{volatility*100:.2f}%",
            'Sharpe Ratio': f"{sharpe:.2f}",
            'Drawdown Máximo': f"{max_drawdown*100:.2f}%",
            'VaR 95% (Diário)': f"{var_95*100:.2f}%",
            'CVaR 95% (Diário)': f"{cvar_95*100:.2f}%",
            'Retorno Médio Diário': f"{returns.mean()*100:.3f}%",
        }
        return metrics
    
    def monte_carlo_simulation(self, days=252, simulations=1000):
        """Simulação de Monte Carlo"""
        returns = self.data['Close'].pct_change().dropna()
        last_price = self.data['Close'].iloc[-1]
        
        mu = returns.mean()
        sigma = returns.std()
        
        simulations_df = pd.DataFrame()
        for i in range(min(simulations, 500)):  # Limite de 500 simulações para performance
            daily_returns = np.random.normal(mu, sigma, days)
            price_path = last_price * (1 + daily_returns).cumprod()
            simulations_df[i] = price_path
        
        return simulations_df
    
    def get_fundamentals(self):
        """Obtém dados fundamentalistas"""
        try:
            ticker_obj = yf.Ticker(self.ticker)
            info = ticker_obj.info
            
            fundamentals = {
                'P/L': info.get('trailingPE', 'N/A'),
                'P/VP': info.get('priceToBook', 'N/A'),
                'ROE': info.get('returnOnEquity', 'N/A'),
                'Margem Líquida': info.get('profitMargins', 'N/A'),
                'Dividend Yield': info.get('dividendYield', 'N/A'),
                'Market Cap': info.get('marketCap', 'N/A'),
                'Setor': info.get('sector', 'N/A'),
            }
            
            # Formatar valores
            for key, value in fundamentals.items():
                if value != 'N/A' and isinstance(value, (int, float)):
                    if key == 'Dividend Yield':
                        fundamentals[key] = f"{value*100:.2f}%"
                    elif key == 'Margem Líquida':
                        fundamentals[key] = f"{value*100:.2f}%"
                    elif key == 'ROE':
                        fundamentals[key] = f"{value*100:.2f}%"
                    elif key == 'Market Cap':
                        fundamentals[key] = f"R$ {value/1e9:.2f}B"
                    elif key in ['P/L', 'P/VP']:
                        fundamentals[key] = f"{value:.2f}"
            
            return fundamentals
        except:
            return {}

# ==================== INTERFACE PRINCIPAL ====================

def main():
    # Cabeçalho
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white;">📊 WealthMaster Pro</h1>
        <p style="color: white; margin: 0;">Plataforma Avançada de Análise de Investimentos</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🎯 Configurações")
        
        # Entrada do ativo
        ticker_input = st.text_input("Ativo", value="PETR4.SA", help="Ex: PETR4.SA, VALE3.SA, AAPL")
        
        # Datas
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Data inicial", datetime(2023, 1, 1))
        with col2:
            end_date = st.date_input("Data final", datetime.today())
        
        # Parâmetros de simulação
        st.markdown("### 💰 Simulação")
        investment = st.number_input("Valor investido (R$)", min_value=100.0, value=10000.0, step=1000.0)
        monthly_contribution = st.number_input("Aporte mensal (R$)", min_value=0.0, value=500.0, step=100.0)
        
        # Seleção de análises
        st.markdown("### 📈 Análises")
        show_technical = st.checkbox("Análise Técnica", value=True)
        show_fundamentals = st.checkbox("Fundamentos", value=True)
        show_risk = st.checkbox("Métricas de Risco", value=True)
        show_monte_carlo = st.checkbox("Monte Carlo", value=True)
        
        st.markdown("---")
        st.markdown("💡 **Dica:** Passe o mouse sobre os gráficos para mais detalhes")
    
    # Processamento principal
    if ticker_input:
        try:
            # Instancia o analisador
            analyzer = WealthAnalyzer(ticker_input, start_date, end_date)
            
            if analyzer.data is not None and not analyzer.data.empty:
                
                # ==================== INFO BÁSICA ====================
                st.markdown(f"## 📈 {ticker_input.upper()}")
                
                # Métricas principais
                col1, col2, col3, col4 = st.columns(4)
                
                current_price = analyzer.data['Close'].iloc[-1]
                price_change = (current_price - analyzer.data['Close'].iloc[0]) / analyzer.data['Close'].iloc[0] * 100
                
                with col1:
                    st.metric("Preço Atual", f"R$ {current_price:.2f}", f"{price_change:+.2f}%")
                with col2:
                    volume_medio = analyzer.data['Volume'].mean() if 'Volume' in analyzer.data.columns else 0
                    st.metric("Volume Médio", f"{volume_medio:,.0f}")
                with col3:
                    high_52w = analyzer.data['Close'].max()
                    st.metric("Máxima 52 semanas", f"R$ {high_52w:.2f}")
                with col4:
                    low_52w = analyzer.data['Close'].min()
                    st.metric("Mínima 52 semanas", f"R$ {low_52w:.2f}")
                
                # ==================== GRÁFICO PRINCIPAL ====================
                st.markdown("### 📊 Evolução do Preço")
                
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                    vertical_spacing=0.05, 
                                    row_heights=[0.7, 0.3])
                
                # Candlestick
                fig.add_trace(go.Candlestick(
                    x=analyzer.data.index,
                    open=analyzer.data['Open'],
                    high=analyzer.data['High'],
                    low=analyzer.data['Low'],
                    close=analyzer.data['Close'],
                    name="Preço"
                ), row=1, col=1)
                
                # Bandas de Bollinger
                fig.add_trace(go.Scatter(
                    x=analyzer.data.index,
                    y=analyzer.data['BB_Upper'],
                    line=dict(color='rgba(255, 255, 0, 0.5)', dash='dash'),
                    name="BB Superior"
                ), row=1, col=1)
                
                fig.add_trace(go.Scatter(
                    x=analyzer.data.index,
                    y=analyzer.data['BB_Lower'],
                    line=dict(color='rgba(255, 255, 0, 0.5)', dash='dash'),
                    name="BB Inferior",
                    fill='tonexty'
                ), row=1, col=1)
                
                # Volume
                if 'Volume' in analyzer.data.columns:
                    colors = ['red' if close < open else 'green' 
                              for close, open in zip(analyzer.data['Close'], analyzer.data['Open'])]
                    fig.add_trace(go.Bar(
                        x=analyzer.data.index,
                        y=analyzer.data['Volume'],
                        marker_color=colors,
                        name="Volume"
                    ), row=2, col=1)
                
                fig.update_layout(
                    title="Análise Técnica Avançada",
                    template="plotly_dark",
                    height=600,
                    showlegend=True,
                    xaxis_rangeslider_visible=False
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # ==================== ANÁLISE TÉCNICA ====================
                if show_technical:
                    st.markdown("### 🔍 Sinais Técnicos")
                    
                    signals = analyzer.get_technical_signals()
                    cols = st.columns(len(signals))
                    for idx, (signal_name, signal_value, signal_class) in enumerate(signals):
                        with cols[idx]:
                            st.markdown(f"""
                            <div class="info-box">
                                <h4>{signal_name}</h4>
                                <p class="{signal_class}">{signal_value}</p>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Indicadores adicionais
                    st.markdown("#### 📊 Indicadores Técnicos")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig_rsi = go.Figure()
                        fig_rsi.add_trace(go.Scatter(x=analyzer.data.index, y=analyzer.data['RSI'], name="RSI", line=dict(color='#00ff88')))
                        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Sobrecomprado")
                        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Sobrevendido")
                        fig_rsi.update_layout(title="RSI (14 períodos)", template="plotly_dark", height=300)
                        st.plotly_chart(fig_rsi, use_container_width=True)
                    
                    with col2:
                        fig_macd = go.Figure()
                        fig_macd.add_trace(go.Scatter(x=analyzer.data.index, y=analyzer.data['MACD'], name="MACD", line=dict(color='#00ff88')))
                        fig_macd.add_trace(go.Scatter(x=analyzer.data.index, y=analyzer.data['MACD_Signal'], name="Sinal", line=dict(color='orange')))
                        fig_macd.add_bar(x=analyzer.data.index, y=analyzer.data['MACD_Hist'], name="Histograma", marker_color='gray')
                        fig_macd.update_layout(title="MACD", template="plotly_dark", height=300)
                        st.plotly_chart(fig_macd, use_container_width=True)
                
                # ==================== FUNDAMENTOS ====================
                if show_fundamentals:
                    st.markdown("### 🏢 Análise Fundamentalista")
                    fundamentals = analyzer.get_fundamentals()
                    
                    if fundamentals:
                        cols = st.columns(4)
                        for idx, (key, value) in enumerate(fundamentals.items()):
                            with cols[idx % 4]:
                                st.metric(key, value)
                    else:
                        st.info("Dados fundamentalistas não disponíveis para este ativo")
                
                # ==================== MÉTRICAS DE RISCO ====================
                if show_risk:
                    st.markdown("### ⚠️ Métricas de Risco")
                    risk_metrics = analyzer.calculate_risk_metrics()
                    
                    cols = st.columns(3)
                    for idx, (key, value) in enumerate(risk_metrics.items()):
                        with cols[idx % 3]:
                            st.metric(key, value)
                    
                    # Gráfico de Drawdown
                    returns = analyzer.data['Close'].pct_change()
                    cumulative_returns = (1 + returns).cumprod()
                    rolling_max = cumulative_returns.expanding().max()
                    drawdown = (cumulative_returns - rolling_max) / rolling_max
                    
                    fig_dd = go.Figure()
                    fig_dd.add_trace(go.Scatter(x=analyzer.data.index, y=drawdown*100, 
                                                fill='tozeroy', name="Drawdown",
                                                line=dict(color='red', width=2)))
                    fig_dd.update_layout(title="Drawdown Histórico (%)", template="plotly_dark", height=300)
                    st.plotly_chart(fig_dd, use_container_width=True)
                
                # ==================== SIMULAÇÃO DE MONTE CARLO ====================
                if show_monte_carlo:
                    st.markdown("### 🎲 Simulação de Monte Carlo")
                    
                    with st.spinner("Executando simulações..."):
                        simulations = analyzer.monte_carlo_simulation(days=252, simulations=500)
                        
                        if not simulations.empty:
                            # Estatísticas da simulação
                            final_prices = simulations.iloc[-1]
                            percentiles = np.percentile(final_prices, [5, 50, 95])
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Cenário Pessimista (5%)", f"R$ {percentiles[0]:.2f}")
                            with col2:
                                st.metric("Cenário Base (50%)", f"R$ {percentiles[1]:.2f}")
                            with col3:
                                st.metric("Cenário Otimista (95%)", f"R$ {percentiles[2]:.2f}")
                            
                            # Gráfico das simulações
                            fig_mc = go.Figure()
                            
                            # Amostra de algumas simulações
                            for i in range(min(100, simulations.shape[1])):
                                fig_mc.add_trace(go.Scatter(
                                    x=simulations.index,
                                    y=simulations[i],
                                    mode='lines',
                                    line=dict(width=0.5, color='rgba(100, 100, 100, 0.3)'),
                                    showlegend=False
                                ))
                            
                            # Percentis
                            fig_mc.add_trace(go.Scatter(
                                x=simulations.index,
                                y=np.percentile(simulations, 95, axis=1),
                                mode='lines',
                                line=dict(color='green', width=2),
                                name='Percentil 95%'
                            ))
                            
                            fig_mc.add_trace(go.Scatter(
                                x=simulations.index,
                                y=np.percentile(simulations, 5, axis=1),
                                mode='lines',
                                line=dict(color='red', width=2),
                                name='Percentil 5%',
                                fill='tonexty'
                            ))
                            
                            fig_mc.update_layout(
                                title="Simulação de Monte Carlo - 500 Cenários",
                                template="plotly_dark",
                                height=500,
                                xaxis_title="Dias à frente",
                                yaxis_title="Preço (R$)"
                            )
                            
                            st.plotly_chart(fig_mc, use_container_width=True)
                            
                            # Probabilidades
                            current_price = analyzer.data['Close'].iloc[-1]
                            prob_up = (final_prices > current_price).mean() * 100
                            prob_down = (final_prices < current_price).mean() * 100
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Probabilidade de Alta", f"{prob_up:.1f}%")
                            with col2:
                                st.metric("Probabilidade de Baixa", f"{prob_down:.1f}%")
                        else:
                            st.warning("Não foi possível realizar a simulação")
                
                # ==================== PROJEÇÃO DE PATRIMÔNIO ====================
                st.markdown("### 💰 Projeção de Patrimônio")
                
                months = 60  # 5 anos
                # Retorno mensal médio
                daily_returns = analyzer.data['Close'].pct_change().dropna()
                monthly_return = (1 + daily_returns).prod() ** (21/len(daily_returns)) - 1 if len(daily_returns) > 0 else 0.01
                
                patrimony = [investment]
                aportes_acumulados = [investment]
                
                for i in range(months):
                    patrimony.append(patrimony[-1] * (1 + monthly_return) + monthly_contribution)
                    aportes_acumulados.append(aportes_acumulados[-1] + monthly_contribution)
                
                fig_proj = go.Figure()
                fig_proj.add_trace(go.Scatter(
                    x=list(range(months + 1)),
                    y=patrimony,
                    mode='lines+markers',
                    name='Patrimônio Projetado',
                    line=dict(color='#00ff88', width=3),
                    marker=dict(size=4)
                ))
                
                fig_proj.add_trace(go.Scatter(
                    x=list(range(months + 1)),
                    y=aportes_acumulados,
                    mode='lines',
                    name='Total Aportado',
                    line=dict(color='orange', width=2, dash='dash')
                ))
                
                fig_proj.update_layout(
                    title=f"Projeção de {months//12} anos com aportes mensais de R$ {monthly_contribution:,.2f}",
                    template="plotly_dark",
                    height=400,
                    xaxis_title="Meses",
                    yaxis_title="Valor (R$)"
                )
                
                st.plotly_chart(fig_proj, use_container_width=True)
                
                # Lucro projetado
                lucro_projetado = patrimony[-1] - aportes_acumulados[-1]
                rentabilidade_projetada = (patrimony[-1] / aportes_acumulados[-1] - 1) * 100
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Patrimônio Final", f"R$ {patrimony[-1]:,.2f}")
                with col2:
                    st.metric("Total Aportado", f"R$ {aportes_acumulados[-1]:,.2f}")
                with col3:
                    st.metric("Lucro Projetado", f"R$ {lucro_projetado:,.2f}", f"{rentabilidade_projetada:.1f}%")
                
                # ==================== COMPARADOR DE ATIVOS ====================
                st.markdown("### 🔄 Comparador de Ativos")
                
                compare_tickers = st.text_input("Compare com outros ativos (separados por vírgula)", 
                                               placeholder="Ex: VALE3.SA, ITUB4.SA, BBDC4.SA")
                
                if compare_tickers:
                    tickers_list = [t.strip() for t in compare_tickers.split(',')]
                    tickers_list.append(ticker_input)
                    
                    fig_comp = go.Figure()
                    
                    for tkr in tickers_list:
                        try:
                            data_comp = yf.download(tkr, start=start_date, end=end_date, progress=False)
                            if not data_comp.empty:
                                returns_comp = (data_comp['Close'] / data_comp['Close'].iloc[0] - 1) * 100
                                fig_comp.add_trace(go.Scatter(
                                    x=returns_comp.index,
                                    y=returns_comp,
                                    mode='lines',
                                    name=tkr.replace('.SA', ''),
                                    line=dict(width=2)
                                ))
                        except:
                            st.warning(f"Não foi possível carregar {tkr}")
                    
                    fig_comp.update_layout(
                        title="Comparativo de Retornos (%)",
                        template="plotly_dark",
                        height=400,
                        xaxis_title="Data",
                        yaxis_title="Retorno (%)"
                    )
                    
                    st.plotly_chart(fig_comp, use_container_width=True)
                
                # ==================== ESTATÍSTICAS ADICIONAIS ====================
                with st.expander("📊 Estatísticas Avançadas"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Distribuição dos Retornos**")
                        returns = analyzer.data['Close'].pct_change().dropna() * 100
                        
                        fig_hist = go.Figure()
                        fig_hist.add_trace(go.Histogram(x=returns, nbinsx=50, name="Retornos"))
                        fig_hist.update_layout(
                            title="Histograma de Retornos Diários (%)",
                            template="plotly_dark",
                            height=300
                        )
                        st.plotly_chart(fig_hist, use_container_width=True)
                    
                    with col2:
                        st.markdown("**Estatísticas Descritivas**")
                        stats_df = pd.DataFrame({
                            'Métrica': ['Média', 'Mediana', 'Desvio Padrão', 'Mínimo', 'Máximo'],
                            'Valor': [
                                f"{returns.mean():.3f}%",
                                f"{returns.median():.3f}%",
                                f"{returns.std():.3f}%",
                                f"{returns.min():.3f}%",
                                f"{returns.max():.3f}%"
                            ]
                        })
                        st.dataframe(stats_df, use_container_width=True)
                
            else:
                st.error("Não foi possível carregar os dados do ativo. Verifique o ticker informado.")
                
        except Exception as e:
            st.error(f"Erro na análise: {str(e)}")
            st.info("Dica: Verifique se o ticker está correto (ex: PETR4.SA, VALE3.SA)")

if __name__ == "__main__":
    main()
