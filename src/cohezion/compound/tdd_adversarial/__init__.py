"""TDD and Adversarial Review sub-package for compound engineering."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.compound.tdd_adversarial.adversarial_review import (
        AdversarialReviewSystem as AdversarialReviewSystem,
    )
    from cohezion.compound.tdd_adversarial.adversarial_review import (
        PerspectiveState as PerspectiveState,
    )
    from cohezion.compound.tdd_adversarial.adversarial_review import (
        ReviewFinding as ReviewFinding,
    )
    from cohezion.compound.tdd_adversarial.adversarial_review import (
        ReviewPerspective as ReviewPerspective,
    )
    from cohezion.compound.tdd_adversarial.adversarial_review import (
        ReviewSession as ReviewSession,
    )
    from cohezion.compound.tdd_adversarial.adversarial_review import (
        get_adversarial_review_system as get_adversarial_review_system,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.tdd_adversarial.adversarial_reviewer import (
        AdversarialCritique as AdversarialCritique,
    )
    from cohezion.compound.tdd_adversarial.adversarial_reviewer import (
        AdversarialRedTeamAgent as AdversarialRedTeamAgent,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.tdd_adversarial.coordinator import (
        TDDAdversarialCoordinator as TDDAdversarialCoordinator,
    )
    from cohezion.compound.tdd_adversarial.coordinator import (
        TDDAdversarialState as TDDAdversarialState,
    )
    from cohezion.compound.tdd_adversarial.coordinator import (
        get_tdd_adversarial_coordinator as get_tdd_adversarial_coordinator,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.tdd_adversarial.tdd_integration import (
        TDDIntegration as TDDIntegration,
    )
    from cohezion.compound.tdd_adversarial.tdd_integration import (
        TDDState as TDDState,
    )
    from cohezion.compound.tdd_adversarial.tdd_integration import (
        TestResult as TestResult,
    )
    from cohezion.compound.tdd_adversarial.tdd_integration import (
        TestStatus as TestStatus,
    )
    from cohezion.compound.tdd_adversarial.tdd_integration import (
        TestType as TestType,
    )
    from cohezion.compound.tdd_adversarial.tdd_integration import (
        get_tdd_integration as get_tdd_integration,
    )
