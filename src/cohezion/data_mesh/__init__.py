"""Data Mesh architecture for Cohezion's multi-agent system.

Maps Zhamak Dehghani's 4 Data Mesh principles to Cohezion:
  1. Domain ownership → Each specialist agent owns its data domain
  2. Data as product  → Typed products with schema, SLA, ownership
  3. Self-serve platform → SurrealDB + Vault + SemanticCache
  4. Federated governance → Compound loop quality gates

Smith fabric mapping: Field fabric (data topology)
  Gauge invariance = governance consistency across domains

Attribution: Zhamak Dehghani, "Data Mesh: Delivering Data-Driven Value at Scale"
  (O'Reilly, 2022)
"""

from cohezion.data_mesh.corpus_quality_consumer import (
    CorpusQualityConsumer as CorpusQualityConsumer,
)
from cohezion.data_mesh.corpus_quality_consumer import (
    make_corpus_quality_consumer as make_corpus_quality_consumer,
)
from cohezion.data_mesh.event_bridge import (
    DataMeshEventBridge as DataMeshEventBridge,
)
from cohezion.data_mesh.event_bridge import (
    make_event_bridge as make_event_bridge,
)
from cohezion.data_mesh.lemonade_multimodal import (
    LemonadeMultimodalClient as LemonadeMultimodalClient,
)
from cohezion.data_mesh.lemonade_multimodal import (
    make_multimodal_client as make_multimodal_client,
)


# Non-destructive wiring: datamesh/ orphan types promoted to data_mesh canonical surface.
# federation.py -> query.py/ingestion.py -> schema.py -> torch, so guard the whole block.
try:
    from cohezion.datamesh.federation import (
        DomainEndpoint as DomainEndpoint,
    )
    from cohezion.datamesh.federation import (
        FederationLayer as FederationLayer,
    )
    from cohezion.datamesh.schema import (
        DataLineage as DataLineage,
    )
    from cohezion.datamesh.schema import (
        Physics12D as Physics12D,
    )
    from cohezion.datamesh.schema import (
        RecordType as RecordType,
    )
    from cohezion.datamesh.schema import (
        UnifiedRecord as UnifiedRecord,
    )
except Exception as _datamesh_import_err:  # pragma: no cover
    import logging as _logging

    _logging.getLogger(__name__).debug(
        "datamesh orphan wiring unavailable (non-fatal): %s", _datamesh_import_err
    )
