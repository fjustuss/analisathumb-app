import os
import requests
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configuração de logging
logging.basicConfig(level=logging.INFO)

# Cria a aplicação Flask
app = Flask(__name__)
CORS(app)

@app.route('/api/analyze', methods=['POST'])
def analyze_endpoint():
    app.logger.info(">>> Rota /api/analyze acessada <<<")
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            app.logger.error("Chave de API (GEMINI_API_KEY) não encontrada no servidor.")
            return jsonify({"error": "Chave de API do Gemini não configurada no servidor."}), 500

        data = request.json
        if not data:
            return jsonify({"error": "Requisição JSON vazia ou mal formatada."}), 400

        # --- NOVA VALIDAÇÃO DE IMAGEM ---
        image_a_data_url = data.get('image_a_data_url')
        if not image_a_data_url:
            app.logger.error("Requisição recebida sem a imagem principal (image_a_data_url).")
            return jsonify({"error": "A imagem principal não foi enviada. Por favor, tente novamente."}), 400
        # --- FIM DA VALIDAÇÃO ---

        title = data.get('title')
        niche = data.get('niche')
        language = data.get('language', 'português')
        
        is_comparison = 'image_b_data_url' in data and data.get('image_b_data_url') is not None

        if is_comparison:
            image_b_data_url = data.get('image_b_data_url')
            if not image_b_data_url:
                 app.logger.error("Modo de comparação ativado, mas a imagem B não foi recebida.")
                 return jsonify({"error": "Modo de comparação ativado, mas a imagem da Versão B não foi enviada."}), 400
            
            app.logger.info(f"Iniciando ANÁLISE COMPARATIVA com Gemini para o nicho '{niche}'.")
            prompt = create_comparison_prompt(title, niche, language)
            image_a_b64 = image_a_data_url.split(',')[1]
            image_b_b64 = image_b_data_url.split(',')[1]
            parts = [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_a_b64}},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_b_b64}}
            ]
        else:
            app.logger.info(f"Iniciando ANÁLISE SIMPLES com Gemini para o nicho '{niche}'.")
            prompt = create_single_analysis_prompt(title, niche, language)
            image_a_b64 = image_a_data_url.split(',')[1]
            parts = [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_a_b64}}
            ]

        endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}'
        payload = {"contents": [{"parts": parts}]}
        
        response = requests.post(endpoint, json=payload)
        app.logger.info(f"Resposta do Gemini (status {response.status_code})")
        response.raise_for_status()

        result_json = response.json()
        
        if 'candidates' not in result_json or not result_json['candidates']:
             raise ValueError("Resposta da API Gemini inválida: sem 'candidates'.")
        
        result_text = result_json['candidates'][0]['content']['parts'][0]['text']
        cleaned_result = result_text.replace("```json", "").replace("```", "").strip()
        final_json = json.loads(cleaned_result)

        return jsonify(final_json)

    except requests.exceptions.HTTPError as e:
        error_text = e.response.text
        app.logger.error(f"Erro HTTP da API externa: {e.response.status_code} - {error_text}")
        return jsonify({"error": f"Erro na API Gemini: {e.response.status_code}. Detalhes: {error_text}"}), e.response.status_code
    except Exception as e:
        app.logger.error(f"Erro inesperado no servidor: {e}")
        return jsonify({"error": f"Ocorreu um erro interno no servidor."}), 500

@app.route('/')
def health_check():
    return "Backend do AnalisaThumb (Gemini Edition) está no ar!"

def create_single_analysis_prompt(title, niche, language):
    """Cria o prompt para análise de uma única thumbnail."""
    return f"""
      Você é o AnalisaThumb, um especialista de classe mundial em otimização de thumbnails e títulos de vídeos do YouTube para maximizar a Taxa de Cliques (CTR).

      **Contexto do Vídeo:**
      - Título: "{title or 'Não fornecido'}"
      - Nicho: "{niche}"
      - Idioma para a Resposta: {language}

      **Sua Tarefa:**
      Realize uma análise completa da thumbnail fornecida.

      **Formato de Saída Obrigatório:**
      Retorne APENAS um objeto JSON com a seguinte estrutura:
      ```json
      {{
        "analysis_type": "single",
        "details": [
          {{"name": "Legibilidade do Texto", "score": 0-100}},
          {{"name": "Impacto Emocional", "score": 0-100}},
          {{"name": "Foco e Composição", "score": 0-100}},
          {{"name": "Uso de Cores", "score": 0-100}},
          {{"name": "Relevância (Contexto)", "score": 0-100}}
        ],
        "recommendations": ["Recomendação 1", "Recomendação 2"],
        "suggested_titles": ["Sugestão de título 1", "Sugestão de título 2"],
        "trend_analysis": "Análise de tendência do nicho aqui.",
        "color_palette": ["#C0392B", "#F1C40F", "#2980B9", "#ECF0F1"]
      }}
      ```
    """

def create_comparison_prompt(title, niche, language):
    """Cria o prompt para análise comparativa de duas thumbnails."""
    return f"""
      Você é o AnalisaThumb, um especialista de classe mundial em otimização de thumbnails do YouTube para maximizar a Taxa de Cliques (CTR).

      **Contexto do Vídeo (aplica-se a ambas as imagens):**
      - Título: "{title or 'Não fornecido'}"
      - Nicho: "{niche}"
      - Idioma para a Resposta: {language}

      **Sua Tarefa:**
      Você recebeu duas imagens: Imagem A (a primeira) e Imagem B (a segunda).
      1. Analise a Imagem A e a Imagem B individualmente, pontuando cada uma de 0 a 100 nos 5 critérios.
      2. Compare as duas e declare uma "Vencedora" com base no maior potencial de CTR.
      3. Forneça uma justificativa clara e objetiva para sua escolha.

      **Formato de Saída Obrigatório:**
      Retorne APENAS um objeto JSON com a seguinte estrutura:
      ```json
      {{
        "analysis_type": "comparison",
        "version_a": {{
          "details": [
            {{"name": "Legibilidade do Texto", "score": 0-100}},
            {{"name": "Impacto Emocional", "score": 0-100}},
            {{"name": "Foco e Composição", "score": 0-100}},
            {{"name": "Uso de Cores", "score": 0-100}},
            {{"name": "Relevância (Contexto)", "score": 0-100}}
          ]
        }},
        "version_b": {{
          "details": [
            {{"name": "Legibilidade do Texto", "score": 0-100}},
            {{"name": "Impacto Emocional", "score": 0-100}},
            {{"name": "Foco e Composição", "score": 0-100}},
            {{"name": "Uso de Cores", "score": 0-100}},
            {{"name": "Relevância (Contexto)", "score": 0-100}}
          ]
        }},
        "comparison_result": {{
            "winner": "Versão A",
            "justification": "A Versão A é a vencedora pois seu uso de cores contrastantes e a expressão facial mais forte na imagem tendem a gerar um CTR maior para o nicho de '{niche}'."
        }}
      }}
      ```
    """

if __name__ == '__main__':
    app.run(port=os.environ.get("PORT", 5000))
