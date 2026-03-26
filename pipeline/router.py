# Model Router — single source of truth for all AI model names.
# No agent file ever hardcodes a model name — they all call get_model().
# To upgrade a model, change it here and all agents update automatically.

PERPLEXITY_DEEP_RESEARCH = "sonar-deep-research"   # $5-15/1M tokens
PERPLEXITY_SONAR         = "sonar"                  # $1/1M tokens — test mode
CLAUDE_SONNET            = "claude-sonnet-4-5-20251001"
CLAUDE_HAIKU             = "claude-haiku-4-5"       # ~10x cheaper — test mode
DEEPSEEK_V3              = "deepseek-chat"

AGENT_MODELS = {
    "topic_agent":  CLAUDE_SONNET,
    "researcher":   PERPLEXITY_DEEP_RESEARCH,
    "analyst":      CLAUDE_SONNET,
    "fact_checker": DEEPSEEK_V3,
    "writer":       CLAUDE_SONNET,
    "optimiser":    CLAUDE_SONNET,
}

# TEST_MODE equivalents — same agents, cheapest available models
_TEST_AGENT_MODELS = {
    "topic_agent":  CLAUDE_HAIKU,
    "researcher":   PERPLEXITY_SONAR,
    "analyst":      CLAUDE_HAIKU,
    "fact_checker": DEEPSEEK_V3,          # already the cheapest option
    "writer":       CLAUDE_HAIKU,
    "optimiser":    CLAUDE_HAIKU,
}


def get_model(agent_name: str) -> str:
    """Return the model identifier for a given agent name.

    When TEST_MODE=true in .env, returns the cheapest equivalent model
    for every agent so a full end-to-end run costs <$0.01.
    """
    from config.settings import settings  # local import avoids circular dependency
    if settings.TEST_MODE:
        return _TEST_AGENT_MODELS[agent_name]
    return AGENT_MODELS[agent_name]

