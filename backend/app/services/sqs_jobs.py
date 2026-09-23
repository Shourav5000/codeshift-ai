from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time

import boto3

from app.graphs.repository_analysis import repository_analysis_graph
from app.services.analysis_store import get_analysis, update_analysis


logger = logging.getLogger(__name__)

QUEUE_URL = os.getenv("SQS_QUEUE_URL", "").strip()
AWS_REGION = os.getenv("AWS_REGION", "us-east-2").strip()

MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 10

# Keep a running job hidden from other workers, but refresh the
# visibility window periodically so a crashed ECS task does not
# strand the message for 30 minutes.
VISIBILITY_TIMEOUT_SECONDS = 600
VISIBILITY_HEARTBEAT_SECONDS = 240

# Hard ceiling for one full repository-analysis attempt.
ANALYSIS_TIMEOUT_SECONDS = 1200

_sqs_client = None
_sqs_lock = threading.Lock()

_worker_started = False
_worker_lock = threading.Lock()


def _get_sqs():
    global _sqs_client

    if _sqs_client is not None:
        return _sqs_client

    with _sqs_lock:
        if _sqs_client is None:
            _sqs_client = boto3.client(
                "sqs",
                region_name=AWS_REGION,
            )

    return _sqs_client


def enqueue_analysis_job(
    analysis_id: str,
    repository_url: str,
) -> None:
    if not QUEUE_URL:
        raise RuntimeError(
            "SQS_QUEUE_URL is not configured."
        )

    _get_sqs().send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps(
            {
                "analysis_id": analysis_id,
                "repository_url": repository_url,
            }
        ),
    )


def _progress_message(
    current_step: str,
) -> str:
    labels = {
        "initializing": "Initializing repository analysis.",
        "repository_validation": "Repository URL validated.",
        "repository_clone": "Repository cloned.",
        "repository_analysis": "Repository inventory analyzed.",
        "repository_content_collection": "Repository evidence collected.",
        "code_structure_analysis": "Code structure analyzed.",
        "dependency_analysis": "Dependencies analyzed.",
        "vulnerability_analysis": "Dependency vulnerabilities analyzed.",
        "semgrep_analysis": "Static analysis completed.",
        "technical_debt_analysis": "Technical debt analysis completed.",
        "architecture_analysis": "Architecture assessment completed.",
        "modernization_planning": "Modernization plan completed.",
        "code_change_planning": "Code change proposal completed.",
        "code_change_review": "Independent review completed.",
        "test_execution": "Baseline validation completed.",
        "human_approval": "Human approval gate evaluated.",
    }

    return labels.get(
        current_step,
        f"Analysis progress: {current_step}.",
    )


async def _run_analysis(
    analysis_id: str,
    repository_url: str,
) -> None:
    initial_state = {
        "repository_url": repository_url,
        "current_step": "initializing",
        "status": "processing",
        "message": "Repository analysis is running.",
    }

    update_analysis(
        analysis_id,
        initial_state,
    )

    latest_state = dict(
        initial_state
    )

    print(
        f"[codeshift] analysis_id={analysis_id} "
        "stage=initializing",
        flush=True,
    )

    try:
        async with asyncio.timeout(
            ANALYSIS_TIMEOUT_SECONDS
        ):
            async for graph_state in (
                repository_analysis_graph.astream(
                    initial_state,
                    stream_mode="values",
                )
            ):
                if not isinstance(
                    graph_state,
                    dict,
                ):
                    continue

                latest_state = dict(
                    graph_state
                )

                current_step = str(
                    latest_state.get(
                        "current_step",
                        "processing",
                    )
                )

                progress_state = {
                    **latest_state,
                    "repository_url": repository_url,
                    # Keep the public job status non-terminal while
                    # individual LangGraph stages are still running.
                    "status": "processing",
                    "current_step": current_step,
                    "message": _progress_message(
                        current_step
                    ),
                }

                update_analysis(
                    analysis_id,
                    progress_state,
                )

                print(
                    f"[codeshift] analysis_id={analysis_id} "
                    f"stage_completed={current_step}",
                    flush=True,
                )

    except TimeoutError as exc:
        raise RuntimeError(
            "Repository analysis exceeded the "
            f"{ANALYSIS_TIMEOUT_SECONDS}-second execution limit."
        ) from exc

    final_state = {
        **latest_state,
        "repository_url": repository_url,
        "message": (
            "Repository analysis completed successfully."
        ),
    }

    update_analysis(
        analysis_id,
        final_state,
    )

    print(
        f"[codeshift] analysis_id={analysis_id} "
        f"completed status={final_state.get('status')}",
        flush=True,
    )


def _visibility_heartbeat(
    receipt_handle: str,
    stop_event: threading.Event,
) -> None:
    while not stop_event.wait(
        VISIBILITY_HEARTBEAT_SECONDS
    ):
        try:
            _get_sqs().change_message_visibility(
                QueueUrl=QUEUE_URL,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=(
                    VISIBILITY_TIMEOUT_SECONDS
                ),
            )

            print(
                "[codeshift] extended SQS visibility timeout",
                flush=True,
            )

        except Exception:
            logger.exception(
                "Unable to extend SQS message visibility."
            )


def _retry_or_fail(
    message: dict,
    analysis_id: str | None,
    exc: Exception,
) -> None:
    receipt_handle = message["ReceiptHandle"]

    receive_count = int(
        message.get(
            "Attributes",
            {},
        ).get(
            "ApproximateReceiveCount",
            "1",
        )
    )

    logger.exception(
        "Repository analysis job failed "
        "(analysis_id=%s, attempt=%s/%s)",
        analysis_id,
        receive_count,
        MAX_ATTEMPTS,
        exc_info=exc,
    )

    if (
        analysis_id
        and receive_count < MAX_ATTEMPTS
    ):
        existing = (
            get_analysis(analysis_id)
            or {}
        )

        update_analysis(
            analysis_id,
            {
                **existing,
                "status": "queued",
                "current_step": "retrying",
                "error": str(exc),
                "message": (
                    "A transient analysis error occurred. "
                    f"Retrying automatically "
                    f"(attempt {receive_count + 1} "
                    f"of {MAX_ATTEMPTS})."
                ),
            },
        )

        _get_sqs().change_message_visibility(
            QueueUrl=QUEUE_URL,
            ReceiptHandle=receipt_handle,
            VisibilityTimeout=RETRY_DELAY_SECONDS,
        )

        return

    if analysis_id:
        existing = (
            get_analysis(analysis_id)
            or {}
        )

        update_analysis(
            analysis_id,
            {
                **existing,
                "status": "failed",
                "current_step": "failed",
                "error": str(exc),
                "message": (
                    "Repository analysis failed after "
                    f"{receive_count} attempts."
                ),
            },
        )

    _get_sqs().delete_message(
        QueueUrl=QUEUE_URL,
        ReceiptHandle=receipt_handle,
    )


def _process_message(
    message: dict,
) -> None:
    analysis_id = None
    heartbeat_stop = None
    heartbeat_thread = None

    try:
        payload = json.loads(
            message["Body"]
        )

        analysis_id = payload["analysis_id"]
        repository_url = payload["repository_url"]

        existing = get_analysis(
            analysis_id
        )

        if existing is None:
            raise RuntimeError(
                "Analysis record does not exist."
            )

        terminal_statuses = {
            "no_changes_required",
            "awaiting_human_approval",
            "approved",
            "rejected",
            "patch_validated",
            "patch_tests_failed",
            "patch_blocked",
            "committed",
            "pull_request_created",
            "github_publish_failed",
        }

        if existing.get(
            "status"
        ) not in terminal_statuses:
            heartbeat_stop = threading.Event()

            heartbeat_thread = threading.Thread(
                target=_visibility_heartbeat,
                args=(
                    message["ReceiptHandle"],
                    heartbeat_stop,
                ),
                name="codeshift-sqs-visibility-heartbeat",
                daemon=True,
            )

            heartbeat_thread.start()

            asyncio.run(
                _run_analysis(
                    analysis_id,
                    repository_url,
                )
            )

        _get_sqs().delete_message(
            QueueUrl=QUEUE_URL,
            ReceiptHandle=message["ReceiptHandle"],
        )

    except Exception as exc:
        _retry_or_fail(
            message,
            analysis_id,
            exc,
        )

    finally:
        if heartbeat_stop is not None:
            heartbeat_stop.set()

        if heartbeat_thread is not None:
            heartbeat_thread.join(
                timeout=1
            )


def _worker_loop() -> None:
    if not QUEUE_URL:
        return

    while True:
        try:
            response = _get_sqs().receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,
                VisibilityTimeout=(
                    VISIBILITY_TIMEOUT_SECONDS
                ),
                AttributeNames=[
                    "ApproximateReceiveCount"
                ],
            )

            for message in response.get(
                "Messages",
                [],
            ):
                _process_message(
                    message
                )

        except Exception:
            logger.exception(
                "SQS worker loop error."
            )
            time.sleep(5)


def start_sqs_worker() -> None:
    global _worker_started

    if not QUEUE_URL:
        logger.warning(
            "SQS worker not started because "
            "SQS_QUEUE_URL is not configured."
        )
        return

    with _worker_lock:
        if _worker_started:
            return

        threading.Thread(
            target=_worker_loop,
            name="codeshift-sqs-worker",
            daemon=True,
        ).start()

        _worker_started = True

        print(
            "[codeshift] SQS worker started",
            flush=True,
        )