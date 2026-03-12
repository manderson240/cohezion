-- Context Query Functions for Cohezion Vault Graph
-- These functions return token-efficient context for agent consumption.
-- Install: surreal import --conn http://localhost:8001 --ns cohezion --db vault context_functions.surql

-- ─── fn::context_neighborhood ────────────────────────────────────────────────
-- Returns the immediate neighborhood of a neuron: its metadata, outbound
-- targets, inbound sources, and cluster siblings. One call, full local context.
--
-- Usage: SELECT * FROM fn::context_neighborhood(neuron:cortex_sarfatti_post_quantum_mechanics_and_toe_md);
DEFINE FUNCTION fn::context_neighborhood($nid: record<neuron>) {
    LET $n = (SELECT title, activation, stage, cluster_id, aspect, tags,
                     synapse_out, synapse_in, word_count, path
              FROM ONLY $nid);

    LET $outbound = (SELECT out.id AS id, out.title AS title,
                            out.activation AS activation, out.stage AS stage,
                            out.cluster_id AS cluster
                     FROM synapse WHERE in = $nid);

    LET $inbound  = (SELECT in.id AS id, in.title AS title,
                            in.activation AS activation, in.stage AS stage,
                            in.cluster_id AS cluster
                     FROM synapse WHERE out = $nid);

    LET $cluster_top = (SELECT id, title, activation, stage
                        FROM neuron
                        WHERE cluster_id = $n.cluster_id AND id != $nid
                        ORDER BY activation DESC LIMIT 5);

    RETURN {
        neuron: $n,
        outbound: $outbound,
        inbound: $inbound,
        cluster_top: $cluster_top
    };
};

-- ─── fn::context_cluster ─────────────────────────────────────────────────────
-- Returns a cluster summary: top neurons by activation, total count, average
-- activation, coherence score. Useful for "what's in this domain?"
--
-- Usage: SELECT * FROM fn::context_cluster("cortex");
DEFINE FUNCTION fn::context_cluster($cluster_name: string) {
    LET $neurons = (SELECT id, title, activation, stage, synapse_out, synapse_in
                    FROM neuron
                    WHERE cluster_id = $cluster_name
                    ORDER BY activation DESC);

    LET $total = array::len($neurons);
    LET $avg_act = math::mean($neurons.activation);
    LET $coherence = fn::compute_coherence($cluster_name);

    LET $top = (SELECT id, title, activation, stage, synapse_out, synapse_in
                FROM neuron
                WHERE cluster_id = $cluster_name
                ORDER BY activation DESC LIMIT 10);

    RETURN {
        cluster: $cluster_name,
        total_neurons: $total,
        avg_activation: $avg_act,
        coherence: $coherence,
        top_neurons: $top
    };
};

-- ─── fn::context_search ──────────────────────────────────────────────────────
-- Finds neurons by title substring match, returns compact results sorted by
-- activation. Use for "find everything related to X" queries.
--
-- Usage: SELECT * FROM fn::context_search("quantum");
DEFINE FUNCTION fn::context_search($query: string) {
    LET $matches = (SELECT id, title, activation, stage, cluster_id, aspect,
                           synapse_out, synapse_in, path
                    FROM neuron
                    WHERE string::contains(string::lowercase(title), string::lowercase($query))
                       OR string::contains(string::lowercase(<string> tags), string::lowercase($query))
                    ORDER BY activation DESC LIMIT 20);

    RETURN $matches;
};

-- ─── fn::context_hops ────────────────────────────────────────────────────────
-- Returns all neurons reachable within N hops from a starting neuron.
-- Hop 1 = direct neighbors, Hop 2 = neighbors of neighbors.
-- Returns deduplicated results sorted by activation.
--
-- Usage: SELECT * FROM fn::context_hops(neuron:cortex_sarfatti_post_quantum_mechanics_and_toe_md, 2);
DEFINE FUNCTION fn::context_hops($nid: record<neuron>, $depth: int) {
    -- Hop 1: direct connections (both directions)
    LET $hop1_ids = array::union(
        (SELECT VALUE out FROM synapse WHERE in = $nid),
        (SELECT VALUE in FROM synapse WHERE out = $nid)
    );

    IF $depth <= 1 {
        RETURN (SELECT id, title, activation, stage, cluster_id, synapse_out, synapse_in
                FROM neuron WHERE id IN $hop1_ids
                ORDER BY activation DESC);
    };

    -- Hop 2: connections of hop1 neurons
    LET $hop2_ids = array::union(
        (SELECT VALUE out FROM synapse WHERE in IN $hop1_ids AND out != $nid AND out NOT IN $hop1_ids),
        (SELECT VALUE in FROM synapse WHERE out IN $hop1_ids AND in != $nid AND in NOT IN $hop1_ids)
    );

    LET $all_ids = array::union($hop1_ids, $hop2_ids);

    RETURN (SELECT id, title, activation, stage, cluster_id, synapse_out, synapse_in
            FROM neuron WHERE id IN $all_ids
            ORDER BY activation DESC LIMIT 50);
};

-- ─── fn::context_bridges ─────────────────────────────────────────────────────
-- Finds neurons that bridge two clusters — nodes with synapses into both.
-- These are the cross-domain connectors, the most token-valuable context.
--
-- Usage: SELECT * FROM fn::context_bridges("cortex", "sensory");
DEFINE FUNCTION fn::context_bridges($cluster_a: string, $cluster_b: string) {
    -- Neurons in cluster_a that link to cluster_b
    LET $a_to_b = (SELECT VALUE in FROM synapse
                   WHERE in.cluster_id = $cluster_a AND out.cluster_id = $cluster_b);

    -- Neurons in cluster_b that link to cluster_a
    LET $b_to_a = (SELECT VALUE in FROM synapse
                   WHERE in.cluster_id = $cluster_b AND out.cluster_id = $cluster_a);

    LET $bridge_ids = array::union($a_to_b, $b_to_a);

    RETURN (SELECT id, title, activation, stage, cluster_id, synapse_out, synapse_in, path
            FROM neuron WHERE id IN $bridge_ids
            ORDER BY activation DESC LIMIT 20);
};

-- ─── fn::vault_stats ─────────────────────────────────────────────────────────
-- Global vault health snapshot. One call for dashboard-level awareness.
--
-- Usage: SELECT * FROM fn::vault_stats();
DEFINE FUNCTION fn::vault_stats() {
    LET $total = array::len((SELECT id FROM neuron));
    LET $synapses = array::len((SELECT id FROM synapse));
    LET $clusters = (SELECT cluster_id, count() AS n, math::mean(activation) AS avg_act
                     FROM neuron GROUP BY cluster_id ORDER BY n DESC);
    LET $stages = (SELECT stage, count() AS n FROM neuron GROUP BY stage);

    RETURN {
        total_neurons: $total[0].n,
        total_synapses: $synapses[0].n,
        clusters: $clusters,
        stage_distribution: $stages
    };
};
