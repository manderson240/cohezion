"""Janelia FlyEM neuPrint API Client for Drosophila Male CNS Connectome.

Connects directly to HHMI Janelia's public neuPrint HTTP API (https://neuprint.janelia.org)
to retrieve authentic synaptic-resolution connectome subgraphs from the complete
male Drosophila melanogaster Central Nervous System dataset (`male-cns:v1.0`).

Dataset Reference:
- FlyEM Male CNS Connectome (>166,000 neurons, 25.6M+ synapses)
- Published September 3, 2026 by HHMI Janelia, Cambridge, MRC LMB, and Google Research.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class NeuPrintNeuron:
    """A real reconstructed biological neuron from Janelia's Male CNS Connectome."""

    body_id: int
    cell_type: str
    instance: str
    region: str
    status: str
    synapses_out: int = 0
    synapses_in: int = 0


@dataclass(frozen=True, slots=True)
class NeuPrintSynapse:
    """A real synaptic connection between two neurons in the Drosophila CNS."""

    source_id: int
    source_type: str
    target_id: int
    target_type: str
    weight: int  # number of synaptic contacts (connection strength)


class JaneliaNeuPrintClient:
    """Client for querying the live Janelia FlyEM neuPrint API."""

    DEFAULT_BASE_URL: str = "https://neuprint.janelia.org/api"
    DEFAULT_DATASET: str = "male-cns:v1.0"

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        dataset: str = DEFAULT_DATASET,
        auth_token: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.dataset = dataset
        self.auth_token = auth_token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Cohezion-Biological-Connectome-Engine/1.0",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def query_cypher(self, cypher: str, timeout: float | None = None) -> dict[str, Any]:
        """Executes a read-only Cypher query against the neuPrint Neo4j backend."""
        url = f"{self.base_url}/custom/custom"
        payload = {
            "dataset": self.dataset,
            "cypher": cypher,
        }
        data = json.dumps(payload).encode("utf-8")
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid neuPrint URL scheme: {url}")
        req = urllib.request.Request(url, data=data, headers=self._headers(), method="POST")  # noqa: S310

        effective_timeout = timeout if timeout is not None else self.timeout
        try:
            with urllib.request.urlopen(req, timeout=effective_timeout) as resp:  # noqa: S310
                result = json.loads(resp.read().decode("utf-8"))
                return result if isinstance(result, dict) else {"data": []}

        except urllib.error.HTTPError as e:
            logger.error("neuPrint HTTP Error %d: %s", e.code, e.reason)
            raise RuntimeError(f"neuPrint query failed ({e.code}): {e.reason}") from e
        except Exception as e:
            logger.error("neuPrint connection error: %s", e)
            raise

    def fetch_central_complex_subgraph(
        self, limit: int = 50, min_weight: int = 10
    ) -> tuple[list[NeuPrintNeuron], list[NeuPrintSynapse]]:
        """Retrieves real Central Complex (CX) ring attractor and steering circuits.

        Queries Ellipsoid Body compass neurons (EPG), Protocerebral Bridge (PEG),
        and Fan-Shaped Body vector steering neurons (PFL1, PFL2, PFL3).
        """
        cypher = f"""
        MATCH (n:`male-cns_Neuron`)
        WHERE n.type IN ["EPG", "PFL3", "PFL1", "PFL2", "PEG", "Delta7"]
        WITH n LIMIT {limit}
        MATCH (n)-[c:ConnectsTo]->(m:`male-cns_Segment`)
        WHERE c.weight >= {min_weight}
        RETURN n.bodyId as source_id, n.type as source_type, n.instance as source_instance,
               m.bodyId as target_id, m.type as target_type, m.instance as target_instance,
               c.weight as weight
        ORDER BY c.weight DESC
        LIMIT {limit * 2}
        """
        data = self.query_cypher(cypher).get("data", [])

        neurons_dict: dict[int, NeuPrintNeuron] = {}
        synapses: list[NeuPrintSynapse] = []

        for row in data:
            if len(row) < 7:
                continue
            s_id, s_type, s_inst, t_id, t_type, t_inst, weight = (
                row[0],
                str(row[1] or "Unknown"),
                str(row[2] or ""),
                row[3],
                str(row[4] or "Unknown"),
                str(row[5] or ""),
                int(row[6] or 0),
            )

            if s_id not in neurons_dict:
                neurons_dict[s_id] = NeuPrintNeuron(
                    body_id=s_id,
                    cell_type=s_type,
                    instance=s_inst,
                    region="brain",
                    status="Traced",
                )
            if t_id not in neurons_dict:
                neurons_dict[t_id] = NeuPrintNeuron(
                    body_id=t_id,
                    cell_type=t_type,
                    instance=t_inst,
                    region="brain",
                    status="Traced",
                )

            synapses.append(
                NeuPrintSynapse(
                    source_id=s_id,
                    source_type=s_type,
                    target_id=t_id,
                    target_type=t_type,
                    weight=weight,
                )
            )

        return list(neurons_dict.values()), synapses

    def fetch_descending_motor_subgraph(
        self, limit: int = 30, min_weight: int = 5
    ) -> tuple[list[NeuPrintNeuron], list[NeuPrintSynapse]]:
        """Retrieves real Brain-to-Ventral Nerve Cord (VNC) descending pathways.

        Queries rapid yaw/turning motor controllers (DNg13) and pitch controllers (DNp01).
        """
        cypher = f"""
        MATCH (n:`male-cns_Neuron`)
        WHERE n.type STARTS WITH "DN"
        WITH n LIMIT {limit}
        MATCH (n)-[c:ConnectsTo]->(m:`male-cns_Segment`)
        WHERE c.weight >= {min_weight}
        RETURN n.bodyId as source_id, n.type as source_type, n.instance as source_instance,
               m.bodyId as target_id, m.type as target_type, m.instance as target_instance,
               c.weight as weight
        ORDER BY c.weight DESC
        LIMIT {limit * 2}
        """
        data = self.query_cypher(cypher).get("data", [])

        neurons_dict: dict[int, NeuPrintNeuron] = {}
        synapses: list[NeuPrintSynapse] = []

        for row in data:
            if len(row) < 7:
                continue
            s_id, s_type, s_inst, t_id, t_type, t_inst, weight = (
                row[0],
                str(row[1] or "Unknown"),
                str(row[2] or ""),
                row[3],
                str(row[4] or "Unknown"),
                str(row[5] or ""),
                int(row[6] or 0),
            )

            if s_id not in neurons_dict:
                neurons_dict[s_id] = NeuPrintNeuron(
                    body_id=s_id,
                    cell_type=s_type,
                    instance=s_inst,
                    region="brain_vnc_bridge",
                    status="Traced",
                )
            if t_id not in neurons_dict:
                neurons_dict[t_id] = NeuPrintNeuron(
                    body_id=t_id,
                    cell_type=t_type,
                    instance=t_inst,
                    region="ventral_nerve_cord",
                    status="Traced",
                )

            synapses.append(
                NeuPrintSynapse(
                    source_id=s_id,
                    source_type=s_type,
                    target_id=t_id,
                    target_type=t_type,
                    weight=weight,
                )
            )

        return list(neurons_dict.values()), synapses
