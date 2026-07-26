from fastapi import FastAPI, Request
from google import genai
import json
import os

app = FastAPI()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

PROMPT_BASE = """
Você é um sistema de análise de golpes contra idosos.
Analise a conversa abaixo e responda APENAS em JSON, no formato:
{{
  "risco": 0-100,
  "classificacao": "Baixo" | "Médio" | "Alto",
  "motivos": ["motivo 1", "motivo 2"],
  "recomendacao": "texto curto"
}}

Considere como sinais de risco: pedido de PIX/transferência, urgência,
pedido de sigilo, troca de número alegando ser familiar, solicitação
de senha ou código, ameaças, pressão emocional.

Conversa:
{conversa}
"""

@app.post("/analisar")
async def analisar_conversa(request: Request):
    dados = await request.json()
    texto_conversa = dados.get("texto", "")

    prompt = PROMPT_BASE.format(conversa=texto_conversa)
    resposta = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt
    )
    texto_resposta = resposta.text.replace("```json", "").replace("```", "").strip()

    try:
        analise = json.loads(texto_resposta)
    except json.JSONDecodeError:
        return {"erro": "A IA não retornou um JSON válido.", "resposta_bruta": texto_resposta}

    return analise