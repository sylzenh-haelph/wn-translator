from qa.retry_controller import RetryController
from qa.rule_based_qa import run_qa
from storage.progress_db import ProgressDB
from translation.chapter_processor import ChapterProcessor
from translation.translation_engine import TranslationEngine
from translation.model_client import GeminiClient


def build_chapter_processor(progress_dir):
    client = GeminiClient()
    translation_engine = TranslationEngine(client)

    retry_controller = RetryController(
        translation_engine=translation_engine,
        qa_function=run_qa,
        max_retries=2,
    )

    progress_db = ProgressDB(progress_dir)

    return ChapterProcessor(
        retry_controller=retry_controller,
        progress_db=progress_db,
        translation_engine=translation_engine,
        qa_checker=run_qa,
    )
