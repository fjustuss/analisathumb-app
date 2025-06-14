import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

# Cria a aplicação Flask
app = Flask(__name__)

# --- CORREÇÃO DE CORS ---
# Configura o CORS de forma mais explícita para permitir requisições
# da API a partir de qualquer origem. O "*" pode ser trocado pela URL
# do seu frontend no futuro para mais segurança.
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Endpoint de análise que retorna um JSON de sucesso
@app.route('/api/analyze', methods=['POST', 'GET'])
def analyze_endpoint():
    """
    Este endpoint de teste ignora qualquer dado recebido
    e sempre retorna um JSON de sucesso.
    """
    mock_response = {
      "details": [
        {"name": "Teste de Conexão com Backend", "score": 100},
        {"name": "Servidor Python/Flask", "score": 100}
      ],
      "recommendations": [
        "Se você está vendo esta mensagem, a conexão entre o frontend e o backend está funcionando perfeitamente!",
        "O próximo passo é restaurar a lógica original das APIs no backend."
      ]
    }
    return jsonify(mock_response)

# Rota de "health check" para ver se o servidor está no ar
@app.route('/')
def health_check():
    return "Backend do AnalisaThumb está no ar! Estrutura corrigida."

# O Render usa o comando do Gunicorn que vamos configurar.
if __name__ == '__main__':
    app.run(port=5000)
