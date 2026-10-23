"""Asesor Gemini (google-genai) con salida JSON restringida al esquema PlanBase."""
import json
from typing import Any

from app.domain.plan_accion import PlanBase

INSTRUCCIONES = """Eres un asesor estratégico para un micronegocio colombiano (tienda de barrio / café).
Respondes SIEMPRE en español y SOLO con JSON que cumpla el esquema indicado.
Reglas obligatorias:
- Basa cada acción en los datos del contexto y cítalos textualmente en `datos_citados` (cifras concretas).
- NUNCA propongas descuentos superiores al 30%; si propones uno, indícalo en `descuento_pct`.
- No inventes productos, clientes ni cifras que no estén en el contexto.
- Entre 1 y 5 acciones. `riesgo` es bajo, medio o alto.
- Considera los festivos de Colombia y la estacionalidad del contexto.
- Si los datos no alcanzan para responder, dilo en `advertencias`."""


class GeminiAdvisor:
    modo = "gemini"

    def __init__(self, api_key: str, modelo: str = "gemini-2.5-flash"):
        from google import genai  # importación diferida: el módulo solo se necesita con API key
        self._genai = genai
        self._client = genai.Client(api_key=api_key)
        self.modelo = modelo

    def generar(self, pregunta: str, contexto: dict[str, Any], error_previo: str | None = None) -> str:
        from google.genai import types
        prompt = f"Pregunta del dueño del negocio: {pregunta}\n\nContexto analítico (JSON):\n" \
                 f"{json.dumps(contexto, ensure_ascii=False, default=str)}"
        if error_previo:
            prompt += f"\n\nTu respuesta anterior no cumplió el esquema JSON ({error_previo}). Corrígela."
        resp = self._client.models.generate_content(
            model=self.modelo, contents=prompt,
            config=types.GenerateContentConfig(system_instruction=INSTRUCCIONES, temperature=0.2,
                                               response_mime_type="application/json",
                                               response_schema=PlanBase))
        return resp.text or ""
