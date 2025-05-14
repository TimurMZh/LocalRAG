import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "app"))

from services.llm_factory import LLMFactory  # noqa: E402
from pipelines.customer.analyze_ticket import CustomerIntent  # noqa: E402
from pydantic import BaseModel  # noqa: E402

"""
This playground is used to test the LLMFactory and the LLM classes.
"""

llm = LLMFactory(provider="openai")

# --------------------------------------------------------------
# Test your LLM with structured output
# --------------------------------------------------------------


class IntentModel(BaseModel):
    intent: CustomerIntent


intent, completion = llm.create_completion(
    response_model=IntentModel,
    messages=[
        {
            "role": "user",
            "content": "Can I have my invoice for order #123456?",
        },
    ],
)

print(intent)
