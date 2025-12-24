# tar -czf xinference_offline.tar.gz \
#     ~/.xinference/cache \
#     ~/.cache/modelscope

# 解压到相同路径（或保持相对结构）
# tar -xzf xinference_offline.tar.gz -C $HOME

# 保证 HF/MS 缓存能被找到
export MODELSCOPE_CACHE=/data/taosha/embedding_models/model_files/modelscope
export XINFERENCE_MODEL_SRC_DIR=/data/taosha/embedding_models/xinference/cache
export XINFERENCE_HOME=/data/taosha/embedding_models/xinference/db
conda activate vllm_env
nohup xinference-local --host 0.0.0.0 --port 51001 &