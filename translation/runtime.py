from __future__ import annotations

import logging
from pathlib import Path

from config.settings import AppConfig, parse_model_chain
from qa.retry_controller import RetryController
from qa.rule_based_qa import run_qa
from storage.progress_db import ProgressDB
from storage.translation_cache import TranslationCache
from translation.chapter_processor import ChapterProcessor
from translation.model_client import create_model_client
from translation.model_failover import FailoverModelClient
from translation.refinement_engine import RefinementEngine
from translation.translation_engine import TranslationEngine

logger = logging.getLogger(__name__)


def primary_translation_label(config: AppConfig) -> str:
    return f"{config.translation_provider}:{config.translation_model}"


def build_failover_client(
    config: AppConfig,
    *,
    role: str,
    primary_provider: str,
    primary_model: str,
    fallbacks: str,
    max_retries: int,
    timeout: int,
    on_failover=None,
) -> FailoverModelClient:
    """
    Client untuk satu role: model utama, diikuti cadangan berurutan.
    Cadangan dicoba saat client sebelumnya gagal total.
    """
    targets = [
        (primary_provider, primary_model),
        *parse_model_chain(fallbacks),
    ]

    clients = []
    labels = []

    for provider, model in targets:
        clients.append(
            create_model_client(
                provider=provider,
                model=model,
                api_key=config.get_api_key(provider),
                max_retries=max_retries,
                timeout=timeout,
                backoff_base=config.backoff_base,
            )
        )
        labels.append(f"{provider}:{model}")

    def default_notify(label, exc):
        logger.warning(
            "%s gagal di %s, pindah ke cadangan. Penyebab: %s",
            role,
            label,
            exc,
        )

    return FailoverModelClient(
        clients,
        labels=labels,
        on_failover=on_failover or default_notify,
    )


def build_translation_client(
    config: AppConfig,
    on_failover=None,
) -> FailoverModelClient:
    return build_failover_client(
        config,
        role="Translasi",
        primary_provider=config.translation_provider,
        primary_model=config.translation_model,
        fallbacks=config.translation_fallbacks,
        max_retries=config.max_retries,
        timeout=config.timeout,
        on_failover=on_failover,
    )


def build_chapter_processor(
    progress_dir,
    config: AppConfig,
    on_failover=None,
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

    translation_client = build_translation_client(
        config,
        on_failover=on_failover,
    )
    primary_label = primary_translation_label(config)

    translation_engine = TranslationEngine(
        client=translation_client,
    )

    refinement_client = create_model_client(
        provider=config.refinement_provider,
        model=config.refinement_model,
        api_key=config.get_api_key(config.refinement_provider),
        max_retries=config.max_retries,
        timeout=config.timeout,
        backoff_base=config.backoff_base,
    )

    refinement_engine = RefinementEngine(
        client=refinement_client,
    )

    cache = TranslationCache(
        cache_dir=cache_dir,
    )

    progress_db = ProgressDB(
        progress_dir=progress_path,
    )

    retry_controller = RetryController(
        translation_engine=translation_engine,
        refinement_engine=refinement_engine,
        qa_function=run_qa,
        max_retries=config.qa_max_retries,
        cache=cache,
        cache_model=config.translation_model,
        cache_guard=lambda: (
            translation_client.last_used == primary_label
        ),
    )

    return ChapterProcessor(
        retry_controller=retry_controller,
        progress_db=progress_db,
        translation_engine=translation_engine,
        qa_checker=run_qa,
    )
