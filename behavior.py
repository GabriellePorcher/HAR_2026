"""
behavior.py

Model hierarchies of concepts over the universe of a Dempster-Schafer model such as:
  lung_issue -> infectious / non_infectious
    infectious -> viral / bacterian
      viral -> _flu_ / _covid_
      bacterian -> _typical_pneumonia_ / _atypical_pneumonia_
where _symbols_ are the leaves of the hierarchy and belong to the Dempster-Shafer universe.

Also model behavior rules that make some actions necessary when some premises in the Dempster-Shafer model are verified.

2026-03-19
gabrielle.porcher@lisn.fr
frederic.boulanger@centralesupelec.fr
"""
import datetime
from fractions import Fraction
from typing import Any, Optional

from dempster_shafer import DempsterShafer
from recorder_model import Recorder
from simulation import Event


class Hierarchy[T]:
    """A hierarchy of concepts over the universe of a DempsterShafer model"""
    ds_model : DempsterShafer[T, Any]  # The Dempster-Shafer model
    concepts : dict[T, set[T]]         # The definitions of the concepts (which may use concepts)
    flat_concepts : dict[T, set[T]]    # The flattened definitions of the concepts (in terms of the items in the universe)

    def __init__(self, ds_model : DempsterShafer[T, Any], concepts: dict[T, set[T]]) -> None:
        """Initialize a hierarchy of concepts over the universe of a DempsterShafer model"""
        self.ds_model = ds_model
        self.concepts = concepts
        self.flat_concepts : dict[T, set[T]] = {}
        for c in concepts:
            self.flat_concepts[c] = self.expand_concept(c)

    def expand_concept(self, concept : T) -> set[T]:
        """Recursively expand the definition of a concept in terms of items of the universe"""
        if concept in self.ds_model.universe:
            return {concept}
        if not concept in self.concepts:
            raise ValueError(f"{concept} is not a concept nor in the universe")
        res = set()
        for d in self.concepts[concept]:
            if d in self.ds_model.universe:
                res.add(d)
            if d in self.flat_concepts:
                res.update(self.flat_concepts[d])
            else:
                self.flat_concepts[d] = self.expand_concept(d)
                res.update(self.flat_concepts[d])
        return res

    def flatten_concepts(self, concepts: set[T]) -> set[T]:
        """Flatten a set of concepts into a set of items in the universe"""
        res = set()
        for c in concepts:
            if c in self.flat_concepts:
                res.update(self.flat_concepts[c])
            else:
                res.add(c)
        return res

class Rule[T,A]:
    """A rule that makes actions necessary when some premises are verified.
    The premises may belong to a hierarchy of concepts."""
    premises : set[T]         # The premises of the rule
    flat_premises : set[T]    # The flattened premises (items of the universe of the hierarchy)
    actions : set[A]          # The actions to perform when the premises are verified
    weight : Fraction         # The degree of necessity of the action, in [0, 1]
    hierarchy : Hierarchy[T]  # The hierarchy of concepts used for the premises

    def __init__(self, premises : set[T], actions : set[A], weight : Fraction, hierarchy : Hierarchy[T]) -> None:
        """Initialize a rule with its premises, actions, weight and hierarchy of concepts."""
        self.premises = premises
        self.flat_premises = hierarchy.flatten_concepts(self.premises)
        self.actions = actions
        self.weight = weight
        self.hierarchy = hierarchy

    def necessity(self):
        """Get the necessity of the actions according to this rule and to the probability of the premises."""
        return min(self.weight, self.hierarchy.ds_model.probability(self.flat_premises))

class Record:
    """A record of some information during a simulation with a Dempster-Shafer model."""
    time : datetime.datetime               # The date and time of the information
    info : dict[int, dict[str, Fraction]]  # The information: the int key corresponds to a subset of the universe
    conflict : Fraction                    # The conflict of the Dempster-Shafer model at that time

    def __init__(self, time : datetime.datetime, info : dict[int, dict[str, Fraction]], conflict : Fraction) -> None:
        """Initialize a record"""
        self.time = time
        self.info = info
        self.conflict = conflict


class BehaviorChecker(Recorder):
    """A model to check the behavior of an agent according to rules and to a DempsterShafer model."""
    rules : list[Rule[str, str]]         # The rules
    no_action_thres : Optional[Fraction] # The threshold under which the actions of a rule should not be performed
    do_action_thres : Optional[Fraction] # The threshold over which the actions of a rule should be performed
    actions_performed : set[str]         # The actions performed so far

    def __init__(self, ds_model : DempsterShafer[str, str]) -> None:
        """Initialize a checker with a DempsterShafer model"""
        super().__init__(ds_model)
        self.rules = []
        self.no_action_thres = None
        self.do_action_thres = None
        self.actions_performed = set()

    def set_rules(self, rules : list[Rule[str, str]]) -> None:
        """Set the rules for this checker"""
        self.rules = rules

    def set_thresholds(self, do_threshold = Fraction('0.7'), no_threshold = Fraction('0.2')) -> None:
        """Set the action/no action thresholds for this checker"""
        self.do_action_thres = do_threshold
        self.no_action_thres = no_threshold

    def process_events(self, events: list[Event[str]]):
        """Process events, updating the Dempster-Shafer model and cheking the behavior according to the rules"""
        super().process_events(events)
        obs = set(map(lambda o: o.data, events))       # Get the observations from the events
        self.actions_performed.update(obs)             # Add the observation to the performed actions TODO: identify actions among observations
        # Check the rules
        for rule in self.rules:
            # TODO: should we perform all actions or only an action among the actions of the rule?
            if self.no_action_thres is None or self.do_action_thres is None:
                raise ValueError("action or no action threshold has not been set!")
            if rule.necessity() > self.do_action_thres and not rule.actions.issubset(self.actions_performed):
                # The actions of the rule are necessary and have not been performed
                print(f"Alert: {rule.actions} should be performed")
            # TODO: what if only some actions of the rule have been performed?
            if rule.necessity() < self.no_action_thres and rule.actions.issubset(self.actions_performed):
                # The actions of the rule are not necessary and have been performed
                print(f"Alert: {rule.actions} should not have been performed")
        print()
