from fastapi import FastAPI, Request, HTTPException
from google import genai
from google.genai import errors as genai_errors
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
    texto_conversa = (dados.get("texto") or "").strip()

    if not texto_conversa:
        raise HTTPException(
            status_code=400,
            detail="Envie um texto não vazio no campo 'texto'.",
        )

    prompt = PROMPT_BASE.format(conversa=texto_conversa)

    try:
        resposta = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )
    except genai_errors.ClientError as e:
        # 429 = cota do Gemini estourada (free tier). Repassamos como 429
        # pro Flutter mostrar uma mensagem amigável em vez de erro genérico.
        status = getattr(e, "code", None) or 500
        if status == 429:
            raise HTTPException(
                status_code=429,
                detail="Limite de análises de IA atingido no momento. Tente novamente mais tarde.",
            )
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao consultar a IA: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro inesperado ao consultar a IA: {e}",
        )

    texto_resposta = resposta.text.replace("```json", "").replace("```", "").strip()

    try:
        analise = json.loads(texto_resposta)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail=f"A IA não retornou um JSON válido. Resposta bruta: {texto_resposta}",
        )

    return analise