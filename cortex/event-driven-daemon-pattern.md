---
title: Event-Driven Daemon Pattern
date: 2026-02-23
tags: [pattern, architecture, async, microservices]
status: active
aspect: knower
neural:
  activation: 0.86
  stage: mature
  synapse_in: 2
  synapse_out: 14
---

# Event-Driven Daemon Pattern

The event-driven daemon pattern is an architecture for long-running background processes that respond to events rather than polling for state changes. Instead of periodically checking queues, databases, or file systems on a fixed interval, the daemon registers event handlers (callbacks, subscriptions, or message consumers) and remains idle until an event arrives, then processes it and returns to waiting.

This pattern combines two well-established concepts: the Unix daemon (a background process with no controlling terminal) and event-driven architecture (EDA), where services communicate asynchronously by producing and consuming events through a message broker or event bus. The result is a service that is resource-efficient (no CPU-burning poll loops), responsive (reacts within milliseconds of event arrival), and naturally decoupled from the systems that produce events.

In microservice architectures, event-driven daemons typically consume from message brokers (Kafka, RabbitMQ, Redis Streams) using patterns such as publish-subscribe or competing consumers. They are the backbone of asynchronous workflows including file sync, data pipeline ingestion, cache invalidation, and background job processing.

## Key Properties

- **Reactive, not proactive** — The daemon sleeps until an event arrives; no wasted CPU cycles on empty polls. Event loop frameworks (asyncio, libuv, epoll) provide the waiting mechanism
- **Loose coupling** — Producers and consumers communicate through events, not direct calls; services can be added, removed, or restarted independently
- **Failure isolation via dead-letter queues** — Failed events are routed to a [[error-handling-with-dlq|DLQ]] after retry exhaustion, preventing poison messages from blocking the pipeline
- **At-least-once delivery and idempotency** — Most brokers guarantee at-least-once delivery; daemons must be idempotent to handle duplicate events safely
- **Backpressure and flow control** — Consumer-side rate limiting prevents overload; message brokers buffer events during downstream slowdowns

## Examples

- **File sync daemon** — Watches a directory via inotify/FSEvents and triggers sync operations when files change, rather than scanning the entire directory tree on a timer
- **Kafka consumer service** — A Python asyncio daemon consuming from a Kafka topic, processing each event through a handler pipeline, and committing offsets only after successful processing
- **Vault context hook** — The Cohezion vault context loader acts as an event-driven daemon, intercepting pre/post events in the AI agent lifecycle to inject and persist vault knowledge
- **SurrealDB sync worker** — Batches agent context writes to [[surrealdb]] triggered by session-end events rather than periodic flushes

## Primary Sources

- Microsoft Azure: Event-Driven Architecture Style — https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/event-driven
- Confluent: Event-Driven Architecture (EDA) Introduction — https://www.confluent.io/learn/event-driven-architecture/
- microservices.io: Event-Driven Architecture Pattern — https://microservices.io/patterns/data/event-driven-architecture.html
- DZone: Architecture Patterns for Reliable Event-Driven Systems — https://dzone.com/articles/reliable-event-driven-architecture-patterns

## Related

- [[lesson-15-system-lockup-2026-01-27]]
- [[lesson-38-singleton-executor-for-sessions-new]]
- [[workflow-orchestration]] — event-driven daemons are a lightweight orchestration pattern for background task coordination
- [[non-blocking-observability]] — daemons must implement non-blocking observability to track events without disrupting the event loop
- [[error-handling-with-dlq]] — DLQ is the standard failure strategy for event-driven daemons when event processing fails
- [[test-isolation-via-singleton-reset]] — daemons often use singletons; the singleton reset pattern enables isolated unit testing of daemon components
- [[2026-02-11-use-event-driven-daemon-for-entire-io|Event-Driven Daemon for IO]] — the decision to adopt this pattern for the Entire-IO sync layer

## Related Concepts

- [[api-design]] — event-driven daemons expose event schemas rather than REST endpoints; schema design is critical for producer-consumer contracts
- [[agent-loop-architecture]] — the agent processing loop mirrors an event-driven daemon: wait for input, process, emit result, repeat
- [[context-management]] — event-driven context hooks manage what information flows into and out of agent sessions
- [[surrealdb-sync-pattern]] — the sync pattern implements event-driven batched writes to the graph database
- [[multi-agent-systems]] — multi-agent architectures use event buses for inter-agent communication, with each agent acting as an event-driven daemon

## Relevance to Cohezion

The event-driven daemon pattern is a foundational architecture in the Cohezion framework. The Entire-IO sync layer, vault context hooks, and SurrealDB sync workers all follow this pattern. The decision to adopt it (documented in [[2026-02-11-use-event-driven-daemon-for-entire-io]]) was driven by the lesson from system lockups caused by blocking poll loops. In Cohezion's [[compound-engineering]] methodology, daemons provide the asynchronous backbone that enables non-blocking agent workflows.
