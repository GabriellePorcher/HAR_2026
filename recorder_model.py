"""
recorder_model.py

A model that records data about some subsets of the Dempster-Shafer universe.

2026-04-02
gabrielle.porcher@lisn.fr
frederic.boulanger@centralesupelec.fr
"""
import datetime
from matplotlib import pyplot as plt

from dempster_shafer import DempsterShafer, Subset
from simulation import Model, Event


class Record:
    """A record of some information during a simulation with a Dempster-Shafer model."""
    time : datetime.datetime            # The date and time of the information
    info : dict[Subset, dict[str, float]]  # The information: the int key corresponds to a subset of the universe
    conflict : float                    # The conflict of the Dempster-Shafer model at that time

    def __init__(self, time : datetime.datetime, info : dict[Subset, dict[str, float]], conflict : float) -> None:
        """Initialize a record"""
        self.time = time
        self.info = info
        self.conflict = conflict


class Recorder(Model[str]):
    """A model to record the evolution of a DempsterShafer model."""
    ds_model : DempsterShafer[str, str]  # The Dempster-Shafer model
    recorded : list[Subset]                 # The subsets to record during the simulation
    records : list[Record]               # The list of information records

    def __init__(self, ds_model : DempsterShafer[str, str]) -> None:
        """Initialize a checker with a DempsterShafer model"""
        self.ds_model = ds_model
        self.recorded = []
        self.records = []

    def set_recorded(self, recorded: list[set[str]]) -> None:
        """Set the list of subsets of the universe for which data should be recorded"""
        self.recorded = list(map(self.ds_model.powerset.abstraction, recorded))
        self.records = []

    def get_records(self) -> list[Record]:
        """Returns and clears the list of records at the end of a simulation"""
        res = self.records
        self.records = []
        return res

    def process_events(self, events: list[Event[str]]):
        """Process events, updating the Dempster-Shafer model and cheking the behavior according to the rules"""
        obs = set(map(lambda o: o.data, events))       # Get the observations from the events
        print(f"Time: {self.simulator.current_time}")  # Print the current time in the simulation
        print(obs)                                     # Print the observations
        self.ds_model.observe(obs)                     # Update the Dempster-Shafer model with the observations
        print(self.ds_model)                           # Print the basic info in the DS model
        # Record requested data if any
        if len(self.recorded) > 0:
            info = {}
            for subset in self.recorded:
                # For each required subset of the universe, we memorize the mass, belief, probability and plausibility
                info[subset] = {
                    'mass': self.ds_model.mass_abstr(subset),
                    'belief' : self.ds_model.belief_abstr(subset),
                    'probability' : self.ds_model.probability_abstr(subset),
                    'plausibility' : self.ds_model.plausibility_abstr(subset),
                }
            # Build the record and append it to the list of records
            self.records.append(Record(self.simulator.current_time, info, self.ds_model.conflict()))
        print()

    def translate(self, word, dictionnary):
        if word in dictionnary:
            return dictionnary[word]
        else:
            return word
        
    def display_recorded(self, translation = {}) -> None:
        records = self.get_records()
        # Extract the time in minutes for the records
        timestamps = list(map(lambda x: x.time.hour * 60 + x.time.minute, records))
        # Draw the evolution of the mass, belief, probability and plausibility
        for data in {'mass', 'belief', 'probability', 'plausibility'}:
            plt.figure()
            for state in self.recorded:
                plt.plot(timestamps, list(map(lambda x : x.info[state][data], records)),
                         label=self.translate(str(sorted(list(self.ds_model.powerset.representation(state)))), translation))

            # Draw the evolution of the conflict
            plt.plot(timestamps, list(map(lambda x : x.conflict, records)), label=self.translate('conflict', translation), color='brown')

            plt.xlabel(self.translate('Time', translation))
            plt.ylabel(self.translate(data, translation).capitalize())
            plt.title(f'{self.translate("Evolution of", translation)} {self.translate(data, translation)} {self.translate("and conflict", translation)}')
            plt.legend()
            plt.grid(True)

        # Display all the figures
        plt.show()
