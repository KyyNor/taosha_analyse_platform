# https://github.com/mudler/LocalAI/releases
# https://proxy.gitwarp.com/https://github.com/mudler/LocalAI/releases/download/v3.7.0/local-ai-v3.7.0-linux-amd64
export HF_ENDPOINT=https://hf-mirror.com
./local-ai-v3.7.0-linux-amd64 backends list |grep installed
./local-ai-v3.7.0-linux-amd64 models list |grep installed
# qwen3-embedding-0.6b
# jina-reranker-v1-tiny-en
./local-ai-v3.7.0-linux-amd64