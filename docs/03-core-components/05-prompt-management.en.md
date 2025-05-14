# Prompt Management

The Prompt Management system provides a structured approach to managing and versioning prompts across different pipelines and use cases. It ensures consistency, maintainability, and easy updates of prompts throughout the application.

## Architecture Overview

The system consists of three main components:

1. **Prompt Registry**: Central storage for all prompts
2. **Prompt Templates**: Jinja2-based templates with variables
3. **Prompt Manager**: Service for retrieving and rendering prompts

## Prompt Registry

Prompts are stored in a structured format using YAML files:

```yaml
# prompts/support/ticket_analysis.yaml
version: 1.0
description: "Analyzes customer support tickets for intent and priority"
template: |
  You are an expert customer support analyst. Analyze the following ticket and determine:
  1. The customer's intent
  2. The priority level
  3. Whether escalation is needed

  Ticket Details:
  Sender: {{ sender }}
  Subject: {{ subject }}
  Body: {{ body }}

  Provide your analysis in a structured format.
variables:
  - sender
  - subject
  - body
```

## Prompt Manager

The PromptManager class handles prompt retrieval and rendering:

```python
class PromptManager:
    @staticmethod
    def get_prompt(
        prompt_name: str,
        pipeline: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Retrieve and render a prompt template.
        
        Args:
            prompt_name: Name of the prompt template
            pipeline: Pipeline name (e.g., 'support', 'sales')
            variables: Dictionary of variables for template rendering
            
        Returns:
            Rendered prompt string
        """
        # Load prompt template
        template_path = f"prompts/{pipeline}/{prompt_name}.yaml"
        with open(template_path, "r") as f:
            prompt_data = yaml.safe_load(f)
            
        # Render template
        template = Template(prompt_data["template"])
        return template.render(**(variables or {}))
```

## Usage in Nodes

Prompts are used in LLM nodes through the PromptManager:

```python
class AnalyzeTicket(LLMNode):
    def create_completion(self, context: ContextModel) -> ResponseModel:
        llm = LLMFactory("openai")
        prompt = PromptManager.get_prompt(
            "ticket_analysis",
            pipeline="support",
            variables={
                "sender": context.sender,
                "subject": context.subject,
                "body": context.body
            }
        )
        return llm.create_completion(
            response_model=self.ResponseModel,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Analyze this ticket."}
            ]
        )
```

## Prompt Organization

Prompts are organized by pipeline and use case:

```
prompts/
├── support/
│   ├── ticket_analysis.yaml
│   ├── response_generation.yaml
│   └── escalation_detection.yaml
├── sales/
│   ├── lead_qualification.yaml
│   └── proposal_generation.yaml
└── common/
    ├── summarization.yaml
    └── classification.yaml
```

## Version Control

Each prompt template includes version information:

```yaml
version: 1.0
last_updated: "2024-03-20"
changelog:
  - version: 1.0
    date: "2024-03-20"
    changes:
      - "Initial version"
      - "Added intent classification"
```

## Best Practices

1. **Template Variables**
   - Use clear, descriptive variable names
   - Document all required variables
   - Provide default values when appropriate

2. **Prompt Structure**
   - Keep prompts focused and specific
   - Use clear instructions and examples
   - Include error handling guidance

3. **Versioning**
   - Increment version numbers for changes
   - Document changes in changelog
   - Maintain backward compatibility

4. **Testing**
   - Test prompts with various inputs
   - Validate template rendering
   - Check for missing variables

## Extending the System

To add new prompts:

1. Create a new YAML file in the appropriate pipeline directory
2. Define the template and variables
3. Add version information
4. Update documentation

Example of adding a new prompt:

```yaml
# prompts/support/customer_feedback.yaml
version: 1.0
description: "Analyzes customer feedback for sentiment and key points"
template: |
  Analyze the following customer feedback:
  
  Feedback: {{ feedback }}
  Rating: {{ rating }}
  
  Identify:
  1. Overall sentiment
  2. Key points mentioned
  3. Areas for improvement
  
  Provide your analysis in a structured format.
variables:
  - feedback
  - rating
```

## Configuration

Prompt settings can be configured through environment variables:

```python
# config/prompt_config.py
class PromptSettings:
    default_pipeline: str = "support"
    template_dir: str = "prompts"
    cache_enabled: bool = True
    cache_ttl: int = 3600  # seconds
```

This allows for flexible configuration while maintaining consistency across the application. 