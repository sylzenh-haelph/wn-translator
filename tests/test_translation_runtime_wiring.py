from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import translation.runtime as runtime
from config.settings import AppConfig


def test_runtime_wires_translation_and_refinement_roles(monkeypatch, tmp_path):
    created_clients = []

    class FakeClient:
        def __init__(self, provider, model):
            self.provider = provider
            self.model = model

    def fake_create_model_client(
        *,
        provider,
        model,
        api_key,
        max_retries,
        timeout,
        backoff_base,
    ):
        client = FakeClient(provider, model)
        created_clients.append(client)
        return client

    class FakeTranslationEngine:
        def __init__(self, client):
            self.client = client

    class FakeRefinementEngine:
        def __init__(self, client):
            self.client = client

    class FakeRetryController:
        def __init__(
            self,
            translation_engine,
            refinement_engine,
            qa_function,
            max_retries,
            cache,
            cache_model,
        ):
            self.translation_engine = translation_engine
            self.refinement_engine = refinement_engine
            self.cache_model = cache_model

    class FakeProgressDB:
        def __init__(self, progress_dir):
            self.progress_dir = progress_dir

    class FakeTranslationCache:
        def __init__(self, cache_dir):
            self.cache_dir = cache_dir

    class FakeChapterProcessor:
        def __init__(
            self,
            retry_controller,
            progress_db,
            translation_engine,
            qa_checker,
        ):
            self.retry_controller = retry_controller
            self.progress_db = progress_db
            self.translation_engine = translation_engine
            self.qa_checker = qa_checker

    monkeypatch.setattr(
        runtime,
        "create_model_client",
        fake_create_model_client,
    )
    monkeypatch.setattr(
        runtime,
        "TranslationEngine",
        FakeTranslationEngine,
    )
    monkeypatch.setattr(
        runtime,
        "RefinementEngine",
        FakeRefinementEngine,
    )
    monkeypatch.setattr(
        runtime,
        "RetryController",
        FakeRetryController,
    )
    monkeypatch.setattr(
        runtime,
        "ProgressDB",
        FakeProgressDB,
    )
    monkeypatch.setattr(
        runtime,
        "TranslationCache",
        FakeTranslationCache,
    )
    monkeypatch.setattr(
        runtime,
        "ChapterProcessor",
        FakeChapterProcessor,
    )

    config = AppConfig(
        translation_provider="openrouter",
        translation_model="translation-model",
        research_provider="openrouter",
        research_model="research-model",
        refinement_provider="gemini",
        refinement_model="refinement-model",
        orchestration_provider="gemini",
        orchestration_model="orchestration-model",
    )

    processor = runtime.build_chapter_processor(
        tmp_path / "progress",
        config,
    )

    assert len(created_clients) == 2

    translation_client = created_clients[0]
    refinement_client = created_clients[1]

    assert translation_client.provider == "openrouter"
    assert translation_client.model == "translation-model"

    assert refinement_client.provider == "gemini"
    assert refinement_client.model == "refinement-model"

    assert (
        processor.retry_controller.refinement_engine.client
        is refinement_client
    )
    assert (
        processor.retry_controller.translation_engine.client
        is translation_client
    )
    assert (
        processor.retry_controller.cache_model
        == "translation-model"
    )
