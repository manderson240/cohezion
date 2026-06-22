"""TDD and Adversarial Review sub-package for compound engineering."""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.compound.tdd_adversarial.adversarial_review import (
        AdversarialReviewSystem as AdversarialReviewSystem,
        PerspectiveState as PerspectiveState,
        ReviewFinding as ReviewFinding,
        ReviewPerspective as ReviewPerspective,
        ReviewSession as ReviewSession,
        get_adversarial_review_system as get_adversarial_review_system,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.tdd_adversarial.adversarial_reviewer import (
        AdversarialCritique as AdversarialCritique,
        AdversarialRedTeamAgent as AdversarialRedTeamAgent,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.tdd_adversarial.coordinator import (
        TDDAdversarialCoordinator as TDDAdversarialCoordinator,
        TDDAdversarialState as TDDAdversarialState,
        get_tdd_adversarial_coordinator as get_tdd_adversarial_coordinator,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.tdd_adversarial.tdd_integration import (
        TDDIntegration as TDDIntegration,
        TDDState as TDDState,
        TestResult as TestResult,
        TestStatus as TestStatus,
        TestType as TestType,
        get_tdd_integration as get_tdd_integration,
    )
