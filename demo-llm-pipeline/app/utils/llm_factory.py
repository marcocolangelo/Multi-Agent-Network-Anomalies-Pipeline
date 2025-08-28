from langchain_community.llms import fake
from app.utils.config import settings
from app.utils.tracing import log

def get_llm():
    """
    Return an Ollama-backed LangChain LLM if the server responds,
    otherwise fall back to a deterministic FakeListLLM.
    """
    try:
        from langchain_ollama import OllamaLLM
        # Attempt a very small health-check call
        llm = OllamaLLM(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0
        )
        llm.invoke("ping")  # ≈1-token check
        log("LLM Factory ▶ using Ollama backend")  # success
        return llm
    except Exception as err:
        log(f"LLM Factory ▶ Ollama unreachable → using FakeListLLM ({err})", "warning")
        return fake.FakeListLLM(responses=["VALID", "Sample report.", "INVALID"])
