import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "app"))

from services.prompt_loader import PromptManager  # noqa: E402

"""
This playground is used to test the PromptManager and the prompts themselves.
"""

# --------------------------------------------------------------
# Test support prompt
# --------------------------------------------------------------

support_prompt = PromptManager.get_prompt(
    "ticket_analysis", pipeline="support", ticket={}
)
print(support_prompt)

# --------------------------------------------------------------
# Test helpdesk prompt
# --------------------------------------------------------------

helpdesk_prompt = PromptManager.get_prompt(
    "ticket_analysis", pipeline="helpdesk", ticket={}
)
print(helpdesk_prompt)
