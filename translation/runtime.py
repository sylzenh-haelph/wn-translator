from __future__ import annotations

from pathlib import Path

from config.settings import AppConfig
from qa.retry_controller import RetryController
from qa.rule_based_qa import run_qa
from storage.progress_db import ProgressDB
from storage.translation_cache import TranslationCache
from translation.chapter_processor import ChapterProcessor
from translation.model_client import create_model_client
from translation.translation_engine import TranslationEngine


def build_chapter_processor(
    progress_dir,
    config: AppConfig,
):
    progress_path = Path(progress_dir)

    cache_dir = Path(config.cache_dir)
    if not cache_dir.is_absolute():
        cache_dir = progress_path.parent / cache_dir

    progress_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    cache_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    client = create_model_client(
        provider=config.provider,
        model=config.model,
        api_key=config.api_key,
        max_retries=config.max_retries,
        timeout=config.timeout,
        backoff_base=config.backoff_base,
    )

    translation_engine = TranslationEngine(
        client=client,
    )

    cache = TranslationCache(
        cache_dir=cache_dir,
    )

    progress_db = ProgressDB(
        progress_dir=progress_path,
    )

    retry_controller = RetryController(
        translation_engine=translation_engine,
        qa_function=run_qa,
        max_retries=config.qa_max_retries,
        cache=cache,
        cache_model=config.model,
    )

    return ChapterProcessor(
        retry_controller=retry_controller,
        progress_db=progress_db,
        translation_engine=translation_engine,
        qa_checker=run_qa,
    )
