# Model Router — single source of truth for all AI model names.
# No agent file ever hardcodes a model name — they all call get_model().
# To upgrade a model, change it here and all agents update automatically.

PERPLEXITY_DEEP_RESEARCH = "sonar-deep-research"
CLAUDE_SONNET            = "claude-sonnet-4-5-20251001"
DEEPSEEK_V3              = "deepseek-chat"

AGENT_MODELS = {
    "topic_agent":  CLAUDE_SONNET,
    "researcher":   PERPLEXITY_DEEP_RESEARCH,
    "analyst":      CLAUDE_SONNET,
    "fact_checker": DEEPSEEK_V3,
    "writer":       CLAUDE_SONNET,
    "optimiser":    CLAUDE_SONNET,
}


def get_model(agent_name: str) -> str:
    """Return the model identifier for a given agent name."""
    return AGENT_MODELS[agent_name]

