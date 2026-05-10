"""
worker.py — Drains the deferred queue when defer_until has passed.

The carbon-aware scheduler's promise is "run this batch job later, in a
greener window." The queue captures the decision; this worker is what
actually fulfils it. Wired to a Timer trigger in function_app.py.

Stage ownership: Agent 4. Calls back into Agent 1's _call_model and
build_receipt because those live in gateway/ — that's the natural seam
between "scheduling" and "executing".
"""

from __future__ import annotations
import logging
import os

from scheduler.deferred_queue import (
    DeferredJob,
    get_ready_jobs,
    mark_processing,
    mark_done,
)
from scheduler.carbon_scheduler import get_routing_decision

logger = logging.getLogger(__name__)


def _process_one(job: DeferredJob) -> bool:
    """Run a single ready job through the pipeline minus the cache check.
    Returns True on success. Never raises — failures are logged and the
    job is left in 'processing' state so the operator can investigate."""
    # Late imports avoid a gateway → scheduler → gateway circular import at
    # module load. Both modules are warm by the time the timer fires.
    from gateway.orchestrator import _call_model
    from gateway.receipt import build_receipt
    from gateway.storage import append_receipt
    from compression.compressor import compress_prompt
    from shared.models import CacheResult

    # Re-compress (deterministic for the same prompt) and re-route as
    # realtime so we don't loop the job back into the deferred queue.
    compression = compress_prompt(job.prompt)
    routing = get_routing_decision(compression.compressed_prompt, urgency="realtime")
    api_key = os.environ.get(routing.api_key_env, "")

    response_text, total_tokens = _call_model(
        prompt=compression.compressed_prompt,
        system_prompt=job.system_prompt,
        model=routing.model,
        endpoint=routing.endpoint,
        api_key=api_key,
        max_tokens=500,
    )

    mark_done(job.job_id, response_text)

    receipt = build_receipt(
        cache_result=CacheResult(hit=False, response=None, similarity=0.0),
        compression=compression,
        routing=routing,
        total_tokens=total_tokens,
        original_prompt_tokens=compression.original_tokens,
    )
    append_receipt(receipt)

    logger.info(
        "Worker: job %s done — carbon at queue=%.0fg/kWh, at run=%.0fg/kWh "
        "(model=%s, region=%s, tokens=%d)",
        job.job_id,
        job.carbon_intensity_at_queue,
        routing.carbon_intensity,
        routing.model,
        routing.region,
        total_tokens,
    )
    return True


def process_ready_jobs() -> int:
    """Drain every job whose defer_until has passed.
    Returns the number of jobs successfully completed.
    Safe to call repeatedly; concurrent calls are best-effort, not transactional."""
    ready = get_ready_jobs()
    if not ready:
        return 0

    logger.info("Worker tick: %d deferred job(s) ready to process", len(ready))
    completed = 0
    for job in ready:
        if not mark_processing(job.job_id):
            continue
        try:
            if _process_one(job):
                completed += 1
        except Exception:
            logger.exception("Worker: job %s failed during processing", job.job_id)
    return completed
