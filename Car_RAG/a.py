from netfree_unstrict_ssl import unstrict_ssl
unstrict_ssl()
from rag.model_client import get_supported_models
supported_models = get_supported_models()

print("Supported models:")
for model in supported_models:
    print(model)