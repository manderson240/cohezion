---
title: "Data Pipelines"
date: 2026-03-04
tags: [concept, data-engineering, infrastructure, architecture]
aspect: knower
neural:
  activation: 0.79
  stage: mature
  synapse_in: 5
  synapse_out: 10
---

# Data Pipelines

## Definition

A data pipeline is a system of processes that moves data from one or more sources through a series of transformation, validation, and enrichment stages to a destination system where it can be consumed for analytics, machine learning, or operational use. Data pipelines automate the flow of data, ensuring that downstream systems receive consistent, timely, and correctly formatted information. The two dominant patterns are ETL (Extract, Transform, Load), which transforms data before loading into a target system, and ELT (Extract, Load, Transform), which loads raw data first and transforms within the target data warehouse.

## Key Properties

- **ETL vs. ELT:** ETL applies transformation rules before loading, suitable for structured data with strict schemas and compliance requirements. ELT loads raw data into cloud warehouses (Snowflake, BigQuery, Databricks) and transforms in-place using SQL or dbt, enabling faster iteration and exploratory analytics. Modern organizations often adopt hybrid approaches.
- **Batch vs. streaming:** Batch processing collects and processes data in scheduled intervals (hourly, daily), optimized for high-volume, latency-tolerant workloads. Streaming (Apache Kafka, Apache Flink) processes data continuously as events arrive, enabling real-time dashboards, fraud detection, and alerting. Micro-batching (Spark Structured Streaming) offers a middle ground.
- **Orchestration:** Tools like Apache Airflow, Dagster, and Prefect manage pipeline DAGs (directed acyclic graphs), handling scheduling, dependency resolution, retry logic, and monitoring. Orchestration ensures pipelines run reliably at scale.
- **Data quality and observability:** Modern pipelines incorporate schema validation, data contracts, anomaly detection, and lineage tracking to ensure data quality. Tools like Great Expectations, dbt tests, and Monte Carlo provide automated quality checks and alerting.
- **Idempotency and exactly-once semantics:** Well-designed pipelines produce the same result regardless of how many times they run (idempotent). For streaming pipelines, exactly-once processing guarantees via checkpointing and watermarking prevent data duplication or loss.

## Examples

- A retail company's nightly ETL pipeline extracts transaction data from point-of-sale systems, transforms it (currency conversion, deduplication, aggregation), and loads summary tables into a data warehouse for business intelligence dashboards.
- Uber's real-time streaming pipeline processes millions of ride events per second using Apache Kafka and Flink, enabling dynamic pricing, driver matching, and ETA estimation in real-time.
- dbt (data build tool) implements the ELT pattern by defining SQL-based transformation models that run inside the data warehouse, with built-in testing and documentation.

## Primary Sources

- Kleppmann, M. (2017). *Designing Data-Intensive Applications*. O'Reilly Media. [dataintensive.net](https://dataintensive.net/)
- Reis, J. & Housley, M. (2022). *Fundamentals of Data Engineering*. O'Reilly Media.
- Narkhede, N., Shapira, G. & Palino, T. (2017). *Kafka: The Definitive Guide*. O'Reilly Media.

## Related Concepts

- [[context-management]] — agent context flow mirrors data pipeline patterns of extraction, transformation, and delivery
- [[workflow-orchestration]] — orchestration tools manage pipeline execution, scheduling, and dependencies
- [[edge-computing]] — edge processing forms the first collection stage of data pipelines
- [[machine-learning]] — ML model training and feature engineering depend on well-structured data pipelines
- [[multi-agent-systems]] — multi-agent data flows follow pipeline patterns with specialized processing stages
- [[data-analysis]] — the downstream consumer of data pipeline outputs

## Related Papers

- [[data-engineering-ai-era-2026]] — the evolution of data engineering practices in the AI era
- [[schema-design-relational]] — relational schema design as the structural foundation for data pipeline destinations
- [[operational-data-ai-agents]] — operational data management for AI agent systems
- [[service-layer-architecture]] — service layers provide stable API boundaries that data pipelines consume

## Relevance to Cohezion

Data pipelines are fundamental to Cohezion's architecture. The research pipeline that ingests papers into the vault follows an ETL pattern: extract metadata and content from sources, transform via NLP enrichment and wiki-link resolution, and load into the Obsidian vault and SurrealDB knowledge graph. The agent context flow -- from raw observation through embedding and retrieval -- mirrors streaming pipeline architectures, with the knowledge graph serving as the persistent data store.
