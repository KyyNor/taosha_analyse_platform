# tar -czf xinference_offline.tar.gz \
#     ~/.xinference/cache \
#     ~/.cache/modelscope

# 解压到相同路径（或保持相对结构）
# tar -xzf xinference_offline.tar.gz -C $HOME

# 保证 HF/MS 缓存能被找到
export MODELSCOPE_CACHE=/data/taosha/xinference/modelscope
export XINFERENCE_MODEL_SRC_DIR=/data/taosha/xinference/cache
export XINFERENCE_HOME=/data/taosha/xinference/db

export XINFERENCE_DISABLE_IMAGE_MODELS=1
uv run xinference-local --host 0.0.0.0 --port 9997