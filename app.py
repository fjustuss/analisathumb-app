import os
import json
import logging # Adicionado para debug
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- CONFIGURAÇÃO DE LOGGING ---
# Para garantir que vejamos as mensagens no log do Render
logging.basicConfig(level=logging.INFO)

# Cria a aplicação Flask
app = Flask(__name__)

# --- CORREÇÃO DE CORS ---
# Configura o CORS de forma mais explícita para permitir requisições
# da API a partir de qualquer origem.
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Endpoint de análise que retorna um JSON de sucesso
@app.route('/api/analyze', methods=['POST', 'GET'])
def analyze_endpoint():
    """
    Este endpoint de teste ignora qualquer dado recebido
    e sempre retorna um JSON de sucesso, com logging adicional.
    """
    # Log para ver se a função foi chamada
    app.logger.info(">>> Rota /api/analyze foi acessada com sucesso! <<<")

    mock_response_data = {
      "details": [
        {"name": "Teste de Conexão com Backend", "score": 100},
        {"name": "Servidor Python/Flask", "score": 100}
      ],
      "recommendations": [
        "Se você está vendo esta mensagem, a conexão entre o frontend e o backend está funcionando perfeitamente!",
        "O próximo passo é restaurar a lógica original das APIs no backend."
      ]
    }
    
    # Criamos a resposta JSON
    response = jsonify(mock_response_data)
    
    # Adicionamos o cabeçalho CORS manualmente para garantir (redundante mas seguro)
    response.headers.add('Access-Control-Allow-Origin', '*')
    
    app.logger.info(f">>> Enviando resposta do backend.")
    
    return response

# Rota de "health check" para ver se o servidor está no ar
@app.route('/')
def health_check():
    app.logger.info(">>> Rota / (health check) foi acessada. <<<")
    return "Backend do AnalisaThumb está no ar! Estrutura corrigida."

# O Render usa o comando do Gunicorn que configuramos.
if __name__ == '__main__':
    app.run(port=5000)
