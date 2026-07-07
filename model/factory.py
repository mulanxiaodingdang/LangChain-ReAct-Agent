import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from utils.config_handler import rag_conf, agent_conf

SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")

chat_model = ChatOpenAI(
    model=rag_conf["chat_model_name"],
    base_url=SILICONFLOW_BASE_URL,
    api_key=SILICONFLOW_API_KEY,
    timeout=agent_conf.get("llm_timeout", 120),
    max_retries=agent_conf.get("llm_max_retries", 3),
)

embed_model = OpenAIEmbeddings(
    model=rag_conf["embedding_model_name"],
    base_url=SILICONFLOW_BASE_URL,
    api_key=SILICONFLOW_API_KEY,
)
