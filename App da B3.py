try:
    df, ibov, news = get_full_data(ticker, data_compra, data_venda)

    # VALIDAÇÃO DE SEGURANÇA: Verifica se o DataFrame tem dados antes de prosseguir
    if df is None or df.empty or len(df) < 1:
        st.warning(f"⚠️ Sem dados para {busca} entre essas datas. Tente recuar a 'Data de Venda' em 1 ou 2 dias.")
    else:
        # Limpeza MultiIndex
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        if isinstance(ibov.columns, pd.MultiIndex): ibov.columns = ibov.columns.get_level_values(0)

        precos = df['Close'].dropna().squeeze()
        precos_ibov = ibov['Close'].dropna().squeeze()
        
        # Sincronização: garante que só comparamos datas que existem em ambos
        idx = precos.index.intersection(precos_ibov.index)
        
        if len(idx) < 1:
            st.error("❌ Erro de sincronização: As datas selecionadas não possuem dados de mercado válidos.")
        else:
            precos, precos_ibov = precos.loc[idx], precos_ibov.loc[idx]

            # PEGANDO OS PREÇOS COM SEGURANÇA
            p_ini = float(precos.iloc[0])
            p_fim = float(precos.iloc[-1]) # Aqui é onde dava o erro; agora validamos o tamanho antes
            
            # Cálculos Financeiros (Quantidade voltou!)
            investido = p_ini * qtd
            bruto = p_fim * qtd
            dividendos = df['Dividends'].loc[idx].sum() * qtd
            lucro_liquido = (bruto - investido) + dividendos - (taxa * 2)
            rent_perc = (lucro_liquido / investido) * 100
            rent_ibov = ((precos_ibov.iloc[-1] / precos_ibov.iloc[0]) - 1) * 100

            # --- RENDERIZAÇÃO DA INTERFACE ---
            st.title(f"Dashboard Quantitativo: {busca}")
            
            c1, c2, c3, c4 = st.columns(4)
            def fmt(v): return f"R$ {v:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
            c1.metric("Total Investido", fmt(investido))
            c2.metric("Valor Final + Div", fmt(bruto + dividendos))
            c3.metric("Lucro Líquido", fmt(lucro_liquido), delta=f"{rent_perc:.2f}%")
            c4.metric("Vs Ibovespa", f"{(rent_perc - rent_ibov):+.2f}%")

            # Gráfico de Performance
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=precos.index, y=(precos/p_ini)*100, name=busca, line=dict(color='#34a853', width=3)))
            fig.add_trace(go.Scatter(x=precos_ibov.index, y=(precos_ibov/precos_ibov.iloc[0])*100, name="IBOVESPA", line=dict(color='#5f6368', dash='dot')))
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                              margin=dict(l=0,r=0,t=20,b=0), xaxis=dict(fixedrange=True), yaxis=dict(side="right", ticksuffix="%", fixedrange=True))
            st.plotly_chart(fig, use_container_width=True)

            # Botão da IA Gemini (Já com sua chave padrão)
            st.divider()
            if st.button("✨ Gerar Insight da IA (Gemini 1.5)"):
                with st.spinner("Analisando fundamentos e notícias..."):
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    headlines = [n['title'] for n in news[:5]] if news else ["Nenhuma notícia recente encontrada."]
                    prompt = f"Analise o ativo {busca}. Retorno: {rent_perc:.2f}% vs Ibov: {rent_ibov:.2f}%. Notícias: {headlines}. Explique o motivo da variação como um economista."
                    response = model.generate_content(prompt)
                    st.info(response.text)

except Exception as e:
    st.error(f"Erro inesperado: {e}")
