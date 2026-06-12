Contents
-
This project implements a Dempster-Shafer theory-based model for scenarios involving uncertainty and ignorance.
It simulates a pneumonia diagnosis process, updating beliefs over time using temporal Dempster-Shafer combination.
The system evaluates actions based on rules and operators from possibility theory,
and triggers alerts for low-value performed actions or high-value unperformed actions with persistence checks.

Dependencies:
--
- Python 3.8+
- matplotlib for data visualization

File Structure:
--
- `dempster_shafer.py`: core Dempster-Shafer logic, with tools for working with power sets.
- `simulation.py`: simple discrete event simulator
- `recorder_model.py`a simulation model for recording information and displaying graphs at the end of the simulation
- `behavior.py` : modeling and checking the behavior of an agent according to rules and abstract classes of diseases
- `model_dsl.py` : the parsers for the different DSLs for describing models, behavior checking and scenarios
- `scenario_pneumo.py`: the pneumonia diagnosis scenario.
- `scenario_grippe_avc.py`: the flu + stroke diagnosis scenario.
- The `.ifx`files describe the scenarios and their different aspects (Dempster-Shafer model, behavior rules, occurrence of events).

Usage:
--
```python scenario_pneumo.py```

```python scenario_grippe_avc.py```

References:
--
Dempster Shafer Theory: [en.wikipedia.org/wiki/Dempster–Shafer_theory](https://en.wikipedia.org/wiki/Dempster%E2%80%93Shafer_theory)

Possibility theory: [en.wikipedia.org/wiki/Possibility_theory](https://en.wikipedia.org/wiki/Possibility_theory)

Contact
--
[__gabrielle.porcher@lisn.fr__](mailto:gabrielle.porcher@lisn.fr)

[frederic.boulanger@centralesupelec.fr](mailto:frederic.boulanger@centralesupelec.fr)

[nicolas.sabouret@universite-paris-saclay.fr](mailto:nicolas.sabouret@universite-paris-saclay.fr)
