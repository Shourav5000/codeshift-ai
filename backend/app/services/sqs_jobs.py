from __future__ import annotations

import asyncio
import json
import os
import threading
import time

import boto3

from app.graphs.repository_analysis import repository_analysis_graph
from app.services.analysis_store import get_analysis, update_analysis


QUEUE_URL = os.getenv("SQS_QUEUE_URL", "").strip()
AWS_REGION = os.getenv("AWS_REGION", "us-east-2").strip()

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

    try:
        result = await repository_analysis_graph.ainvoke(
            initial_state
        )

        result["repository_url"] = repository_url
        result["message"] = (
            "Repository analysis completed successfully."
        )

        update_analysis(
            analysis_id,
            result,
        )

    except Exception as exc:
        update_analysis(
            analysis_id,
            {
                **initial_state,
                "status": "failed",
                "current_step": "failed",
                "error": str(exc),
                "message": "Repository analysis failed.",
            },
        )
        raise


def _process_message(
    message: dict,
) -> None:
    receipt_handle = message["ReceiptHandle"]

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
            "failed",
        }

        if existing.get("status") not in terminal_statuses:
            asyncio.run(
                _run_analysis(
                    analysis_id,
                    repository_url,
                )
            )

        _get_sqs().delete_message(
            QueueUrl=QUEUE_URL,
            ReceiptHandle=receipt_handle,
        )

    except Exception as exc:
        try:
            payload = json.loads(
                message.get("Body", "{}")
            )

            analysis_id = payload.get(
                "analysis_id"
            )

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
                        "message": "Repository analysis failed.",
                    },
                )

                _get_sqs().delete_message(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=receipt_handle,
                )

        except Exception:
            # If AWS/ECS itself fails, leave the message in SQS.
            # It becomes visible again after the visibility timeout.
            pass


def _worker_loop() -> None:
    if not QUEUE_URL:
        return

    while True:
        try:
            response = _get_sqs().receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,
                VisibilityTimeout=1800,
            )

            for message in response.get(
                "Messages",
                [],
            ):
                _process_message(
                    message
                )

        except Exception:
            time.sleep(5)


def start_sqs_worker() -> None:
    global _worker_started

    if not QUEUE_URL:
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
