import openai # Você precisaria adicionar 'openai' ao requirements.txt

# --- NOVA SEÇÃO DE ANÁLISE COM IA ---
st.divider()
st.subheader("🤖 Análise Inteligente do Período (Beta)")

# Use st.secrets no Streamlit Cloud para gerenciar sua chave com segurança
# Para testar localmente, você pode colocar a string diretamente (mas não suba pro GitHub assim!)
# openai.api_key = st.secrets["OPENAI_API_KEY"] 
openai.api_key = "SUA_CHAVE_API_DA_OPENAI_AQUI" 

if st.button("🧠 Solicitar Análise da IA sobre Movimentações"):
    with st.spinner('A IA está lendo o gráfico e buscando notícias...'):
        
        # 1. Coletar as Notícias via yfinance
        try:
            stock_context = yf.Ticker(ticker)
            news = stock_context.news
            # Pega as 5 notícias mais relevantes
            headlines = [n['title'] for n in news[:5]]
            news_text = "\n".join(headlines)
        except:
            news_text = "Não foi possível coletar notícias recentes para este ativo."

        # 2. Preparar o contexto técnico
        rendimento_texto = "positivo" if rent_total > 0 else "negativo"
        data_ini_fmt = data_compra.strftime('%d/%m/%Y')
        data_fim_fmt = data_venda.strftime('%d/%m/%Y')

        # 3. Criar o Prompt para o GPT
        prompt = f"""
        Você é um analista financeiro sênior especializado na B3.
        Analise a performance de {busca} entre {data_ini_fmt} e {data_fim_fmt}.
        O ativo teve um rendimento líquido {rendimento_texto} de {rent_total:.2f}%.
        O benchmark Ibovespa rendeu {rent_ibov:.2f}% no mesmo período.
        O Drawdown Máximo foi de {max_drawdown:.2f}%.

        Manchetes relevantes coletadas recentemente sobre o ativo:
        {news_text}

        Redija uma análise concisa (máximo 3 parágrafos) explicando os prováveis motivos técnicos e fundamentalistas para este comportamento de preço. Use linguagem profissional e direta. Se não houver notícias claras, baseie-se no comportamento técnico (volatilidade, tendência).
        """

        # 4. Chamar a API da OpenAI (Usando modelo mais moderno/barato)
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", # Ou "gpt-4-turbo" para análises muito melhores, mas mais caras
                messages=[
                    {"role": "system", "content": "Você é um assistente útil e especialista em finanças."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5 # Controla a criatividade (0.5 é equilibrado para finanças)
            )
            
            analise_ia = response.choices[0].message.content
            
            # 5. Exibir a análise
            st.markdown(f'<div class="status-card" style="border-left-color: #1c83e1; background-color: #1a1e22;"><b>Parecer da IA:</b><br><br>{analise_ia}</div>', unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Erro ao chamar a IA: {e}")
