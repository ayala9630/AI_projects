"""Answers a question from the retrieved chunks, as a Pydantic object with citations."""
from urllib import response

from rag.model_client import chat_completion
from pydantic import BaseModel, Field, ConfigDict

from rag.chunking import Chunk

MODEL = "openai/gpt-oss-120b"

SYSTEM = """אתה עונה על שאלות של לקוחות חברת הרכב "אופק רכב".
ענה רק על סמך הקטעים שבתוך <chunk>. אל תשתמש בידע כללי.

לכל טענה בתשובה, הוסף ציטוט מדויק מתוך הקטע המתאים, מילה במילה.

כללי ציטוט:
1. הציטוט חייב להיות מועתק בדיוק מתוך הקטע.
2. הציטוט חייב לכלול את כל המידע הדרוש לביסוס הטענה.
3. אל תצטט רק חלק ממשפט כאשר ההקשר הקודם או הבא נדרש להבנת הטענה.
4. כאשר שם של רכיב או מוצר מופיע במשפט קודם, כלול גם את המשפט הזה בציטוט.
5. אל תשנה מילים, ניסוח או סדר מילים בציטוט.

אם הקטעים לא מספיקים כדי לענות, החזר insufficient_context=true, בלי ציטוטים.

ענה בעברית, במשפטים קצרים."""


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: str = Field(description="The chunk id, exactly as it appears in <chunk id=...>")
    quote: str = Field(description="An exact quote from that chunk, word for word")


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str
    citations: list[Citation]
    insufficient_context: bool


def build_context(chunks: list[Chunk]) -> str:
    return "\n\n".join(f'<chunk id="{c.id}">\n{c.text}\n</chunk>' for c in chunks)


def ask(question: str, chunks: list[Chunk], client=None) -> tuple[Answer, object]:
    """Returns the parsed Answer and the token usage. Needs GROQ_API_KEY in the environment."""
    if client is None:
        import os
        from groq import Groq

        client = Groq(api_key=os.environ["GROQ_API_KEY"])
        response = chat_completion(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {
                    "role": "user",
                    "content": f"{build_context(chunks)}\n\nשאלה: {question}"
                }
            ],
            max_tokens=4000,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "Answer",
                    "strict": True,
                    "schema": Answer.model_json_schema()
                }
            }
        )
    answer = Answer.model_validate_json(
        response.choices[0].message.content
    )
    if answer.insufficient_context:
        answer.answer = "אין מספיק מידע במקורות כדי לענות על השאלה."
    return answer, response.usage

import re

import re
import unicodedata

import re
import unicodedata

def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)

    # Normalize different dash characters
    text = re.sub(r"[\u2010-\u2015\u2212\u2011]", "-", text)

    # Normalize quotation marks
    text = re.sub(r"[\u2018\u2019]", "'", text)
    text = re.sub(r"[\u201c\u201d]", '"', text)

    # Remove directional marks
    text = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def verify_citations(answer: Answer, chunks: list[Chunk]) -> list[Citation]:
    chunks_by_id = {chunk.id: chunk for chunk in chunks}
    bad_citations = []

    for citation in answer.citations:
        chunk = chunks_by_id.get(citation.chunk_id)

        if chunk is None:
            bad_citations.append(citation)
            continue

        quote = normalize_text(citation.quote)
        text = normalize_text(chunk.text)

        if quote not in text:
            bad_citations.append(citation)

    return bad_citations
