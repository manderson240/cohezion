---
title: Error Handling with Dead Letter Queue
date: 2026-02-23
tags: [pattern, architecture, reliability]
status: active
aspect: knower
neural:
  activation: 0.79
  stage: growing
  synapse_in: 7
  synapse_out: 9
---

## Definition

The Dead Letter Queue (DLQ) pattern routes messages that cannot be processed successfully — after a defined number of retry attempts — to a separate queue for inspection, analysis, and eventual reprocessing. The term originates from postal systems where undeliverable mail is sent to a "dead letter office." In distributed systems, DLQs prevent failed messages from blocking healthy processing, enable forensic analysis of failures, and provide a recovery path that avoids both silent data loss and system-halting crashes.

The pattern addresses a fundamental truth of distributed systems, articulated by Werner Vogels: "Everything fails, all the time." The question is not whether failures will occur, but how the system behaves when they do. Without DLQs, a single poisoned message (malformed payload, schema mismatch, business rule violation) can block an entire processing pipeline. With DLQs, the poisoned message is isolated while healthy messages continue flowing.

## Key Properties

- **Retry-then-quarantine**: Messages are retried with exponential backoff up to a configured maximum attempt count (`maxReceiveCount`); only after exhausting retries does the message move to the DLQ
- **Error classification**: Effective DLQ systems distinguish transient errors (service temporarily unavailable — worth retrying) from permanent errors (malformed data — retrying is futile); only permanent failures should reach the DLQ quickly
- **Idempotent consumers**: Because messages may be retried multiple times, consumer logic must be idempotent — processing the same message twice must produce the same result without side effects
- **Metadata capture**: DLQ messages should carry error metadata (exception type, stack trace, timestamp, retry count, originating queue) for forensic analysis
- **Monitoring and alerting**: A DLQ without monitoring becomes a silent graveyard of lost messages; alerts on queue depth spikes catch systemic failures early

## Implementation Pattern

```
Message arrives → Consumer attempts processing
├─ Success → Acknowledge, remove from queue
└─ Failure → Increment retry counter
    ├─ Retries remaining → Re-enqueue with exponential backoff
    └─ Max retries exceeded → Route to DLQ with error metadata
        └─ DLQ → Monitor, alert, inspect, fix root cause, replay
```

**Non-blocking retry topology** (e.g., Spring Kafka 2.7+): Failed messages route through a series of retry topics with increasing delay (1s, 2s, 4s, 8s) before reaching the dead letter topic. This keeps the main consumer thread unblocked while still providing retry semantics.

## Primary Sources

- Confluent (2025). *Apache Kafka Dead Letter Queue: A Comprehensive Guide*. [https://www.confluent.io/learn/kafka-dead-letter-queue/](https://www.confluent.io/learn/kafka-dead-letter-queue/)
- AWS Documentation. *Using dead-letter queues in Amazon SQS*. [https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)
- OneUptime (2026). *How to Implement Dead Letter Queue Patterns for Failed Message Handling*. [https://oneuptime.com/blog/post/2026-02-09-dead-letter-queue-patterns/view](https://oneuptime.com/blog/post/2026-02-09-dead-letter-queue-patterns/view)

## Related Concepts

- [[non-blocking-observability]] — DLQ is a complementary pattern; non-blocking observability degrades gracefully while DLQ captures failures for retry
- [[workflow-orchestration]] — DLQ provides failure isolation within orchestrated multi-step agent workflows
- [[event-driven-daemon-pattern]] — event-driven daemons use DLQs to handle failed event processing without blocking the main event loop
- [[api-design]] — API error response design determines what error information is available for DLQ metadata capture
- [[service-layer-architecture]] — service layers define the boundary at which DLQ routing decisions are made
- [[multi-agent-systems]] — DLQ pattern is essential for multi-agent systems where individual agent failures must not cascade across the pipeline
- [[agent-architecture]] — DLQ provides the failure isolation layer within Cohezion's agent architecture

## Relevance to Cohezion

DLQs are directly applicable to Cohezion's multi-agent architecture. When the CompoundExecutor delegates tasks to specialized agents, any agent can fail — tool calls time out, LLM responses are malformed, external APIs return errors. Rather than crashing the entire pipeline or silently dropping failed steps, a DLQ pattern captures the failure with full context (agent ID, input payload, error details, retry history) for later inspection and replay. This is especially important for the vault's research pipeline, where a single failed paper analysis should not block processing of the remaining 83+ papers. The pattern complements the existing [[non-blocking-observability]] approach by adding a recovery mechanism to the graceful degradation strategy.

## Related Lessons

- [[lesson-12-layered-validation]] — layered validation catches errors before they reach the DLQ, reducing dead letter volume
- [[lesson-35-non-blocking-observability-pattern-new]] — non-blocking observability is the monitoring complement to DLQ's recovery mechanism

## Skills

- RELIABILITY_FALLBACK_PRIME — Dual-write buffer recovery
