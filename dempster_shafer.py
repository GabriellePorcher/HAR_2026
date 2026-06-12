"""
dempster_shafer.py

A Dempster-Shafer model as presented in: https://en.wikipedia.org/wiki/Dempster%E2%80%93Shafer_theory

A PowerSet class is used to work over the subsets of the universe

The MassFunction class models mass functions and their combination (joint mass)

2026-03-19
gabrielle.porcher@lisn.fr
frederic.boulanger@centralesupelec.fr
"""
from __future__ import annotations

from fractions import Fraction
from typing import Iterable, Tuple, Optional, Any

class Subset:
    """
    A subset of a universe.
    Subsets are represented as integers, each bit corresponding to an element of the universe.
    This makes such subsets usable à dictionary keys, and make the computation of the union, intersection etc. very easy.
    It is also easy to enumerate all the subsets, just by countong from 0 to 2**n - 1 if n is the size of the universe.
    """
    abstraction : int
    """The abstraction of the subset, each bit corresponding to an item of the universe."""

    def __init__(self, abstr : int) -> None:
        self.abstraction = abstr

    def __hash__(self) -> int:
        return hash(self.abstraction)

    def __eq__(self, other: Subset) -> bool:
        return self.abstraction == other.abstraction

    def __ne__(self, other: Subset) -> bool:
        return self.abstraction != other.abstraction

    def union(self, s: Subset) -> Subset:
        return Subset(self.abstraction | s.abstraction)

    def intersection(self, s: Subset) -> Subset:
        return Subset(self.abstraction & s.abstraction)

    def includes(self, other: Subset) -> bool:
        """Return true if this subset includes the 'other' subset.
        This is computed by checking if the other subset is preserved by the intersection with this subset."""
        return self.intersection(other) == other

    def empty(self):
        return self.abstraction == 0

    def cardinality(self) -> int:
        c = 0
        abstr = self.abstraction
        while abstr != 0:
            if abstr & 1 != 0:
                c += 1
            abstr >>= 1
        return c

    def __len__(self) -> int:
        return self.cardinality()

    def __str__(self) -> str:
        return str(self.abstraction)

    def all_subsets_of(self, max_size = None) -> Iterable[Subset]:
        """Build all the subsets of a subset of the universe, limiting thir size to max_size"""
        if max_size is None:
            max_size = self.cardinality()
        indices = self.indices()
        size = len(indices)
        # We build the abstraction of the subsets by counting up to 2**size - 1
        for i in range(1 << size):
            if Subset(i).cardinality() > max_size:
                continue
            # Each bit with value 1 represents the presence of the corresponding element in the subset
            subset = 0
            idx = 0
            while i != 0:
                if i & 1 != 0:
                    subset |= (1 << indices[idx])
                i >>= 1
                idx += 1
            yield Subset(subset)

    def indices(self) -> list[int]:
        """Return the list of the indices of the elements of a subset of the universe"""
        res = []
        idx = 0
        abstr = self.abstraction
        while abstr != 0:
            if abstr & 1 != 0:
                res.append(idx)
            abstr >>= 1
            idx += 1
        return res

    def all_subsets_among(self, among: Iterable[Subset]) -> Iterable[Subset]:
        """Build all the subsets of abstr among a given set of subsets of the universe"""
        for s in among:
            if self.includes(s):
                yield s


class PowerSet[T]:
    """
    The power set of a universe of object of type T.
    The subsets are represented as integers, so enumerating all the subsets of
    the universe amounts to counting from 0 to 2**len(universe) -1.
    Methods are provided to abstract a subset into an integer,
    to get the representation of an integer as a subset, to check for the inclusion
    of subsets, and to compute the intersection and union of subsets.
    """
    universe : list[T]
    """The complete list of the items in the universe"""
    map : dict[T, int]
    """The map from items to their index in the list"""

    def __init__(self, universe: set[T]) -> None:
        """Build a power set from a universe"""
        self.universe = list(universe)
        self.map = {}
        for idx in range(len(self.universe)):
            self.map[self.universe[idx]] = idx

    def __iter__(self) -> Iterable[Subset]:
        """Iterate over the power set"""
        for item in range(1 << len(self.universe)):
            yield Subset(item)

    def abstraction(self, s : set[T]) -> Subset:
        """Return the integer that is the abstraction of a subset.
        The abstraction is defined as an integer from 0 to 2**len(universe) -1.
        The bits corresponding to each item in the subset are set to 1.
        """
        abstr = 0
        for item in s:
            if item not in self.map:
                raise ValueError(f"{item} is not in the universe")
            abstr |= (1 << self.map[item])
        return Subset(abstr)

    def representation(self, abstr : Subset) -> set[T]:
        """Return the subset corresponding to an integer.
        The elements of the subset are those for which the bit is set to 1 in the integer."""
        return {self.universe[idx] for idx in abstr.indices()}


class MassFunction[T]:
    """A Dempster-Shafer mass function over the power set of a universe of objects of type T"""
    value : dict[Subset, Fraction]
    """The value associated to the abstraction of each subset in the powerset"""
    model : DempsterShafer[T,Any]
    """The Dempster-Shafer model over which the mass function are set"""

    #precision : float = 1e-6
    #"""The precision for comparing masses (to zero and for checking that the sum is 1.0)"""

    def __init__(self, value : dict[Subset, Fraction], model: DempsterShafer[T, Any]) -> None:
        """Initialize the MassFunction object"""
        self.value = value
        self.model = model
        if sum(self.value.values()) != Fraction(1):
            raise ValueError(f"The sum of the masses for all subsets should be 1.0 (found {sum(self.value.values())}")
        if self(Subset(0)) != Fraction(0):
            raise ValueError("The mass for the empty set should be 0.0")

    @staticmethod
    def make(mapping : list[Tuple[set[T], Fraction]], model : DempsterShafer[T, Any]) -> MassFunction[T]:
        """Make a MassFunction from a list of pairs (subset, mass), and a model.
        This is used to bypass the fact that dictionnaries are not hashable,
        so the function cannot be specified using a dict[set[T], float]."""

        # Build the dictionary that maps the abstraction of a subset to its mass
        abstract_value = {}
        for (state, mass) in mapping:
            # Check for already existing entry
            subset = model.powerset.abstraction(state)
            if subset in abstract_value.keys():
                raise ValueError(f"Redefinition of the mass of {state}")
            abstract_value[subset] = mass
        return MassFunction(abstract_value, model)


    def __call__(self, arg : Subset) -> Fraction:
        """Call the mass function on subset 'arg'"""
        if arg not in self.value:
            return Fraction(0)  # Unspecified masses are considered as 0.0
        else:
            return self.value[arg]

    def __add__(self, arg : MassFunction[T]) -> Tuple[MassFunction[T], Fraction]:
        """Combine the mass function with another according to the Dempster-Shafer theory"""
        combinedvalue : dict[Subset, Fraction] = {}
        # Firstly, compute the conflict K, which is the sum of the products of the two functions
        # over all pairs of subsets that are not empty and have an empty intersection.
        all_subsets = set(self.value).union(set(arg.value))
        conflict = sum(
                        (self(b) * arg(c)
                            for b in all_subsets
                            for c in all_subsets
                            if not b.empty() and not c.empty() and b.intersection(c).empty()
                        ),
                        start = Fraction(0)
                   )
        # Then, compute the value of the resulting mass function for each state in the powerset
        # In the Dempster-Shafer model, the mass of the empty set is 0.0
        # The mass of a non-empty subset S is the sum of the product of the two functions
        # over all pairs of non-empty subsets whose intersection is S.
        # The result is normalized by dividing it by (1 - K).
        # We consider only the states that can have a non-zero mass
        considered_states = {b.intersection(c)
                                for b in all_subsets
                                for c in all_subsets
                                if not b.intersection(c).empty()
                            }
        for state in considered_states:
            mass = sum(
                        (self(b) * arg(c)
                            for b in all_subsets
                            for c in all_subsets
                            if not b.empty() and not c.empty() and b.intersection(c) == state
                        ),
                        start = Fraction(0)
                    ) / (1-conflict)
            # We consider only non-zero masses
            if mass != Fraction(0):
                combinedvalue[state] = mass
        return (MassFunction(combinedvalue, self.model), conflict)

    def __repr__(self) -> str:
        """Return a string representing the mass function"""
        string = ''
        for (v, m) in self.value.items():
            string += f'{v}: {m}\n'
        return string

class DempsterShafer[T,O]:
    """A Dempster-Shafer model over the power set of a universe of objects of type T,
       with observations of type O."""
    universe : set[T]                         # The universe
    powerset : PowerSet[T]                    # The powerset of the universe, representing all possible states
    observations : set[O]                     # The possible observations
    obs_set : PowerSet[O]                     # The powerset of the observations
    masses : dict[O, MassFunction[T]]         # The mass functions associated to the observations
    global_masses : Optional[MassFunction[T]] # The mass function resulting from the observations made so far (None if no observation yet)
    global_conflict : Optional[Fraction]      # The conflict produced by the observations made so far (None if no observation yet)

    def __init__(self, universe : set[T], observations : set[O]) -> None:
        """Initialize the DempsterShafer object"""
        self.universe = universe
        self.powerset = PowerSet[T](self.universe)
        self.observations = observations
        self.obs_set = PowerSet[O](self.observations)
        self.masses = {}
        self.global_masses = None
        self.global_conflict = None

    def set_mass_funcs(self, masses : list[Tuple[set[O], MassFunction[T]]]) -> None:
        """Set the mass function for each observation.
        When a mass function is associated to a set of observations, it will be used when
        all the observations in the set are made simultaneously, and any mass function
        associated to individual observations will be ignored.
        More precisely, if a set of observations is made, the mass function associated to the largest
        subsets will be used, and mass functions associated to the included observations will be ignored.
        For instance, if {'a', 'b', 'c'} is observed, and there is a mass function associated to {'a', 'b'},
        that mass function will be used, as well as the mass function associated to {'c'}.
        The mass functions associated to {'a'} and {'b'} will be ignored.
        The behavior is undefined when mass functions are associated to several overlaping subsets
        of an observation. For instance, if {'a', 'b', 'c'} is observed, and there are mass functions
        associated both to {'a', 'b'} and to {'b', 'c'}.
        """
        self.masses = {}
        pws = self.obs_set
        for (obs, mass) in masses:
            self.masses[pws.abstraction(obs)] = mass


    def observe(self, observation : set[O]):
        """Update the model according to an observation"""
        current_obs = self.obs_set.abstraction(observation)
        # Find all subsets of the observation that have a mass function.
        # Sort them by decreasing cardinality
        obs_masses = [obs
                        for obs in current_obs.all_subsets_among(self.masses.keys())
                     ]
        obs_masses.sort(key=lambda x : x.cardinality(), reverse=True)

        # Now, keep the mass of the observations that are not included in the previously selected ones
        used_masses : list[Subset] = []
        for obs in obs_masses:
            keep = True
            for used in used_masses:
                if used.includes(obs):
                    keep = False
                    break
                if not used.intersection(obs).empty():
                    # If an observation intersects a larger one without being included, we have a conflict
                    raise ValueError(f"Conflicting mass functions for {self.obs_set.representation(used)} \
                                       and {self.obs_set.representation(obs)}")
            if keep:
                used_masses.append(obs)

        # Update the global mass function by combining the mass functions associated to the observation
        for obs in used_masses:
            if self.global_masses is None:
                # If this is the first observation, just set the global mass function
                self.global_masses = self.masses[obs]
                self.global_conflict = Fraction(0)
            else:
                # Else, combine the mass function of the observation with the previous mass function
                (self.global_masses, self.global_conflict) = self.global_masses + self.masses[obs]

    def mass_func(self, observation: set[O]) -> MassFunction[T]:
        """Get the mass function associated to a set of observations."""
        return self.mass_func_abstr(self.obs_set.abstraction(observation))

    def mass_func_abstr(self, observation: Subset) -> MassFunction[T]:
        """Get the mass function associated to the abstraction of a set of observations."""
        if observation not in self.masses:
            raise ValueError(f"Observation {observation} not in the model")
        return self.masses[observation]

    def mass(self, state: set[T]) -> Optional[Fraction]:
        """Get the global mass of a state."""
        return self.mass_abstr(self.powerset.abstraction(state))

    def mass_abstr(self, state: Subset) -> Optional[Fraction]:
        """Get the global mass of the abstraction of a state."""
        if self.global_masses is None:
            return None
        return self.global_masses(state)

    def conflict(self):
        """Get the current global conflict generated by the observations"""
        return self.global_conflict

    def belief(self, state: set[T]) -> Optional[Fraction]:
        """Get the current belief in a state (lower bound of its probability)"""
        return self.belief_abstr(self.powerset.abstraction(state))

    def belief_abstr(self, state: Subset) -> Optional[Fraction]:
        """Get the current belief in the abstraction of a state (lower bound of its probability)"""
        if self.global_masses is None:
            return None
        return sum(
                    (self.global_masses(b)
                        for b in self.global_masses.value
                        if state.includes(b)
                    ),
                    start = Fraction(0)
                )

    def probability(self, state: set[T]) -> Optional[Fraction]:
        """Get the current pignistic probability of a state"""
        return self.probability_abstr(self.powerset.abstraction(state))

    def probability_abstr(self, state: Subset) -> Optional[Fraction]:
        """Get the current pignistic probability of the abstraction of a state"""
        if self.global_masses is None:
            return None
        return sum(
                    (self.global_masses(b)
                            * state.intersection(b).cardinality()
                            / b.cardinality()
                        for b in self.global_masses.value
                        if not b.empty() and not state.intersection(b).empty()
                    ),
                    start = Fraction(0)
                )

    def plausibility(self, state: set[T]) -> Optional[Fraction]:
        """Get the current plausibility of a state (upper bound of its probability)"""
        return self.plausibility_abstr(self.powerset.abstraction(state))

    def plausibility_abstr(self, state: Subset) -> Optional[Fraction]:
        """Get the current plausibility of the abstratction of a state (upper bound of its probability)"""
        if self.global_masses is None:
            return None
        return sum(
                    (self.global_masses(b)
                        for b in self.global_masses.value
                        if not state.intersection(b).empty()
                    ),
                    start = Fraction(0)
                  )

    def __str__(self):
        """Build a string representation of the model"""
        if self.global_masses is None:
            return f"{self.universe}. No information"
        colwidth = max(map(len, self.universe))
        s = ' '*colwidth + '  mass  bel   prob  plaus\n'
        for item in self.universe:
            s += f'{item:<{colwidth}}: {self.mass({item}):>.2f}  '
            s += f'{self.belief({item}):>.2f}  '
            s += f'{self.probability({item}):>.2f}  '
            s += f'{self.plausibility({item}):>.2f}\n'
        s += f'conflict = {self.global_conflict:<.2f}'
        return s


if __name__ == "__main__":
    # A few checks to see if everything works.
    # It should print :
    """
    Mass function for o1
    1: 0.3
    2: 0.7
    
    Mass function for o2
    1: 0.2
    2: 0.8
    
    m_o1 ⊕ m_o2
    (0: 0.0
    1: 0.0967741935483871
    2: 0.9032258064516128
    3: 0.0
    , 0.38)
    
    Initial Dempster-Shafer model:
    {'a', 'b'}. No information
    
    After observing o1:
        mass  bel   prob  plaus
    a: 0.30  0.30  0.30  0.30
    b: 0.70  0.70  0.70  0.70
    conflict = 0.00
    
    After observing o2:
        mass  bel   prob  plaus
    a: 0.10  0.10  0.10  0.10
    b: 0.90  0.90  0.90  0.90
    conflict = 0.38
    
    After observing o1 and o3:
        mass  bel   prob  plaus
    a: 0.00  0.00  0.00  0.00
    b: 1.00  1.00  1.00  1.00
    conflict = 0.21
    """
    universe = {"a", "b"}
    observations = {"o1", "o2", "o3"}
    ds = DempsterShafer[str, str](universe, observations)
    ds.set_mass_funcs([
        ({'o1'}, MassFunction.make([({'a'}, Fraction('0.3')), ({'b'}, Fraction('0.7'))], ds)),
        ({'o2'}, MassFunction.make([({'a'}, Fraction('0.2')), ({'b'}, Fraction('0.8'))], ds)),
        ({'o1', 'o3'}, MassFunction.make([({'a'}, Fraction('0.1')), ({'b'}, Fraction('0.9'))], ds))
    ])

    print("Mass function for o1")
    print(ds.mass_func({'o1'}))

    print("Mass function for o2")
    print(ds.mass_func({'o2'}))

    print("m_o1 ⊕ m_o2")
    print(ds.mass_func({"o1"}) + ds.mass_func({"o2"}))
    print()

    print("Initial Dempster-Shafer model:")
    print(ds)
    print()

    print("After observing o1:")
    ds.observe({"o1"})
    print(ds)
    print()

    print("After observing o2:")
    ds.observe({"o2"})
    print(ds)
    print()

    print("After observing o1 and o3:")
    ds.observe({"o1", "o2", "o3"})
    print(ds)
