"""
simulation.py

A very simple discrete event simulation engine.

2026-03-19
gabrielle.porcher@lisn.fr
frederic.boulanger@centralesupelec.fr
"""
from __future__ import annotations
import datetime
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any
import heapq

class Event[T]:
    """An event carrying data of type T.
    The comparison operators < and > are defined so that events are ordered according to their time of occurrence"""
    time : datetime.datetime   # The time of occurrence of the event
    data : T                   # The data of the event

    def __init__(self, time, data):
        self.time = time
        self.data = data

    def __lt__(self, other: Event[Any]):
        return self.time < other.time

    def __gt__(self, other: Event[Any]):
        return self.time > other.time

class Simulator[T]:
    """A discrete event simulator"""
    event_queue : list[Event[T]]      # The list of pending events, managed as a min heap
    current_time : datetime.datetime  # The current time (time of the events being processed)

    def __init__(self):
        self.event_queue = []
        self.current_time = datetime.datetime.min

    def add_event(self, event: Event[T]):
        """Add an event to the simulation scenario"""
        heapq.heappush(self.event_queue, event)

    def add_events(self, events: Iterable[Event[T]]):
        """Add some events to the simulation scenario"""
        for event in events:
            self.add_event(event)

    def step(self) -> list[Event[T]]:
        """Compute the events to process for the next simulation step, and advance the siumation time accordingly"""
        if len(self.event_queue) == 0:  # No pending events -> the simulation is finished
            return []
        events = []
        self.current_time = self.event_queue[0].time  # Get the time of the first (next) event
        # Get all the pending events that occur at this time
        while len(self.event_queue) > 0 \
          and self.event_queue[0].time == self.current_time:
            events.append(heapq.heappop(self.event_queue))
        return events

class Model[T](ABC):
    """An abstract class for simulation models"""
    simulator : Simulator[T]  # The simulator of the model

    @abstractmethod
    def process_events(self, events : list[Event[T]]):
        """Process the events at an instant in the simulation."""
        pass

    def set_simulator(self, simu: Simulator[T]):
        """Set the simulator of this model"""
        self.simulator = simu


class Simulation[T]:
    """A discrete event simulation."""
    model : Model[T]     # The model to simulate
    simu : Simulator[T]  # The discrete event simulator

    def __init__(self, model : Model[T]):
        self.model = model
        self.simu = Simulator[T]()
        self.model.set_simulator(self.simu)

    def add_event(self, event: Event[T]):
        """Add an event to the simulation scenario"""
        self.simu.add_event(event)

    def add_events(self, events: Iterable[Event[T]]):
        """Add events to the simulation scenario"""
        self.simu.add_events(events)

    def run(self) -> None:
        """Run the simulation."""
        events = self.simu.step()
        while len(events) > 0:
            self.model.process_events(events)
            events = self.simu.step()


