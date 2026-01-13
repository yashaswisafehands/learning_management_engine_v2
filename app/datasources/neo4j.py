import importlib
import inspect
import logging
import pkgutil

from neomodel import StructuredNode, config

from app.core.config import settings

config.DATABASE_URL = settings.NEO4J_URI
logging.info(f"Neo4j config set to: {config.DATABASE_URL}")


def auto_discover_models():
    import app.models as models_pkg

    model_classes = []
    for _, module_name, _ in pkgutil.iter_modules(models_pkg.__path__):
        module = importlib.import_module(f"{models_pkg.__name__}.{module_name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, StructuredNode) and obj is not StructuredNode:
                model_classes.append(obj)
    return model_classes


def create_indexes_from_models():
    models = auto_discover_models()



# NOTE: Additional performance indexes should be declared on model properties
# using index=True or unique_index=True so they are installed via install_labels.
