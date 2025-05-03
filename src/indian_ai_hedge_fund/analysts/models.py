from pydantic import BaseModel

class AnalystReport(BaseModel):
    signal: str
    confidence: float
    reasoning: str