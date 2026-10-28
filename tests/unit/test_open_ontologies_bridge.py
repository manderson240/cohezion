"""Unit tests for Open Ontologies Bridge & Semantic Verification Engine."""

from cohezion.knowledge_graph.open_ontologies_bridge import (
    BORO4DSpacetimeExtent,
    DerivationCertificate,
    DerivationStep,
    SemanticPlanner,
    SemanticTriple,
)


def test_semantic_triple_digest():
    t1 = SemanticTriple("ex:Person", "rdfs:subClassOf", "ex:Agent")
    t2 = SemanticTriple("ex:Person", "rdfs:subClassOf", "ex:Agent")
    assert t1.digest() == t2.digest()
    assert len(t1.digest()) == 16


def test_semantic_plan_blast_radius_and_consequences():
    planner = SemanticPlanner()

    # Base graph: Alice hasParent Bob
    base = [
        SemanticTriple("ex:Alice", "ex:hasParent", "ex:Bob"),
        SemanticTriple("ex:Bob", "rdf:type", "ex:Person"),
    ]

    # Proposed change: ex:hasParent rdfs:domain ex:Person
    proposed = [
        SemanticTriple("ex:hasParent", "rdfs:domain", "ex:Person"),
    ]

    plan = planner.plan(base, proposed)

    # Consequence should be derived: ex:Alice rdf:type ex:Person
    assert plan.consequence_count >= 1
    assert plan.conservativity == "not_conservative_under_rule_table"
    assert plan.derived_certificate is not None

    # Verify certificate soundness
    is_sound, msg = plan.derived_certificate.verify()
    assert is_sound, f"Certificate verification failed: {msg}"


def test_derivation_certificate_rejects_forged_premise():
    t1 = SemanticTriple("ex:Alice", "ex:hasParent", "ex:Bob")
    t_rule = SemanticTriple("ex:hasParent", "rdfs:domain", "ex:Person")
    t_inferred = SemanticTriple("ex:Alice", "rdf:type", "ex:Person")

    # Step with unknown forged premise digest
    step = DerivationStep(
        step_id="step_1",
        rule_name="rdfs:domain_inference",
        premise_digests=["fake_digest_1234"],
        conclusion=t_inferred,
    )

    cert = DerivationCertificate(
        certificate_id="cert_test",
        asserted_triples=[t1, t_rule],
        derivation_steps=[step],
    )

    is_sound, msg = cert.verify()
    assert not is_sound
    assert "forged premise" in msg.lower() or "unknown premise" in msg.lower()


def test_boro_4d_spacetime_extent():
    extent1 = BORO4DSpacetimeExtent(
        entity_id="contract_1win_sale",
        spatial_bounds=(0.1, 0.2, 0.3),
        temporal_interval=(1700000000.0, 1705000000.0),
        brane_vector=(0.5,) * 8,
    )
    extent2 = BORO4DSpacetimeExtent(
        entity_id="contract_1win_burn",
        spatial_bounds=(0.15, 0.25, 0.35),
        temporal_interval=(1702000000.0, 1708000000.0),
        brane_vector=(0.5,) * 8,
    )

    assert extent1.contains_time(1702500000.0)
    assert not extent1.contains_time(1706000000.0)
    assert extent1.temporal_overlaps(extent2)

    surql = extent1.to_surrealql()
    assert "boro_extent:contract_1win_sale" in surql
    assert "brane_8d" in surql
