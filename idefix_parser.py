"""
idefix_parser.py

A pyparsing parser for Idefix files:
  - Dempset-Shafer model files
  - Behavior checker files
  - Scenario files

2026-04-03
frederic.boulanger@centralesupelec.fr
"""
import datetime
import io
from fractions import Fraction
from typing import Any, Tuple, Optional

import pyparsing as pp
from pyparsing import ParseResults

import behavior
import dempster_shafer
import recorder_model
import simulation


# This section defines classes that are used to store the result of the parsing (aka AST classes)

class Import:
    """Represents the import of another model"""
    uri: str     # The URI of the model
    model: Any   # The model parsed from that URI

    def __init__(self, uri: str, model: Any):
        self.uri = uri
        self.model = model

    def __hash__(self):
        return hash(self.uri)

    def __eq__(self, other):
        return self.uri == other.uri

    def __str__(self):
        rez = "URI: " + self.uri + "\n"
        rez += "Model: \n"
        for item in self.model:
            rez += str(item) + "\n"
        return rez

class MassFunction:
    """A parsed mass function associated to some set of abservations"""
    obs: set[str]
    """"The set of observations to which this mass function is associated"""
    values: list[Tuple[set[str], Fraction]]
    """The list of (subset, mass) pairs that define the mass function"""

    def __init__(self, obs: set[str], values: list[Tuple[set[str], Fraction]]):
        self.obs = obs
        self.values = values

    def as_mass_function(self, ds: dempster_shafer.DempsterShafer) -> dempster_shafer.MassFunction:
        """Turn this 'parsing' mass function into an effective mass function from the Dempster Shafer module"""
        catch = Fraction(1)   # This is used to compute the remaining (not assigned) mass
        for i in range(len(self.values)):
            if len(self.values[i][0]) == 1 and "_uncertain_" in str(self.values[i][0]):
                # The '_uncertain_' keyword represents the whole universe of the Dempster-Shafer model
                self.values[i] = (ds.universe, self.values[i][1])
            if self.values[i][1] != "_catch_":
                # Actual values must be subtracted from catch to compute the remaining mass
                catch -= self.values[i][1]
        # Now, replace the '_catch_' keyword with the remaining mass
        for i in range(len(self.values)):
            if self.values[i][1] == "_catch_":
                self.values[i] = (self.values[i][0], catch)
        return dempster_shafer.MassFunction.make(self.values, ds)

class DSModel:
    """A parsed Dempster-Shafer model"""
    observations: set[str]
    """The set of observations for the mass functions"""
    universe : set[str]
    """The set of all possible states"""
    massfunctions: list[MassFunction]
    """The mass functions that assign a mass to the subsets of the universe according to the observations"""

    def __init__(self, observations: list[str], universe: list[str], masses: list[MassFunction]):
        self.observations = set(observations)
        self.universe = set(universe)
        self.massfunctions = masses

    def as_dempster_shafer(self) -> dempster_shafer.DempsterShafer:
        """Convert to an effective Demster-Shafer model from the dempster_shafer module"""
        ds_model = dempster_shafer.DempsterShafer(self.universe, self.observations)
        massfuncs = []
        for mf in self.massfunctions:
            massfuncs.append((mf.obs, mf.as_mass_function(ds_model)))
        ds_model.set_mass_funcs(massfuncs)
        return ds_model

class Event:
    """A parsed event for the simulation"""
    time: datetime.datetime
    """The time of the event"""
    what: str
    """What occurs at that time"""

    def __init__(self, time: datetime.datetime, what: str):
        self.time = time
        self.what = what

class SCModel:
    """A parsed scenario"""
    events: list[Event]
    """The list of events in the scenario"""
    to_record: list[set[str]]
    """The list of subsets for which the statistics should be recorded"""
    no_action_threshold: Optional[Fraction]
    """The necessity threshold under which an action should not be performed (in association with a behavior model)"""
    do_action_threshold: Optional[Fraction]
    """The necessity threshold over which an action should be performed (in association with a behavior model)"""

    def __init__(self, events: list[Event], to_record: list[set[str]], no_action_thres: Optional[Fraction], do_action_thres: Optional[Fraction]):
        self.events = events
        self.to_record = to_record
        self.no_action_threshold = no_action_thres
        self.do_action_threshold = do_action_thres

class Rule:
    """A parsed rule, determining the necissty of an action according to the state of the model"""
    trigger: list[str]
    """The state (subset of the DS universe) that triggers this rule"""
    weight: Fraction
    """The weight of the rule (I.E. necessity of the action)"""
    action: list[str]
    """The actions that should be performed according to this rule"""

    def __init__(self, trigger: list[str], weight: Fraction, action: list[str]):
        self.trigger = trigger
        self.weight = weight
        self.action = action

    def as_rule(self, hierarchy: behavior.Hierarchy) -> behavior.Rule:
        return behavior.Rule(set(self.trigger), set(self.action), self.weight, hierarchy)

class BHModel:
    """A parsed behavior model"""
    hierarchy: dict[str, set[str]]
    """The hierarchy if concepts over the universe of the DS model"""
    rules: list[Rule]
    """The rules that indicate the necessity of some actions"""

    def __init__(self, hierarchy: list[dict[str, list[str]]], rules: list[Rule]):
        self.hierarchy = {}
        for d in hierarchy:
            for c in d.keys():
                if len(d[c]) == 1 and d[c][0] == '[*]':
                    self.hierarchy[c] = set()
                else:
                    self.hierarchy[c] = set(d[c])
        self.rules = rules

    def as_bh_model(self, ds: dempster_shafer.DempsterShafer) -> behavior.BehaviorChecker:
        """Convert to an effective BehaviorChecker model"""
        bh = behavior.BehaviorChecker(ds)
        hierarchy = behavior.Hierarchy(ds, self.hierarchy)
        rules = []
        for r in self.rules:
            rules.append(r.as_rule(hierarchy))
        bh.set_rules(rules)
        return bh


class Model:
    """A parsed model"""
    version: str
    """The version of the model/syntax"""
    imports: list[Import]
    """The list of imported files"""
    ds_model: Optional[DSModel]
    """The Dempster Shafer model"""
    sc_model: Optional[SCModel]
    """The scenario model"""
    bh_model: Optional[BHModel]
    """The behavior model"""

    def __init__(self):
        self.version = ""
        self.imports = []
        self.ds_model = None
        self.bh_model = None
        self.sc_model = None

    def update(self, parse_res: ParseResults) -> None:
        """Update the value of the model with new parse results"""
        self.version = parse_res["version"]

        imports = set(self.imports)
        for imp in parse_res["imports"]:
            imports.add(imp)
        self.imports = list(imports)

        if "ds_model" in parse_res:
            if self.ds_model is not None:
                raise ValueError("Several Dempster-Shafer models in file")
            self.ds_model = parse_res["ds_model"][0]
        if "bh_model" in parse_res:
            if self.bh_model is not None:
                raise ValueError("Several behavioral models in file")
            self.bh_model = parse_res["bh_model"][0]
        if "sc_model" in parse_res:
            if self.sc_model is not None:
                raise ValueError("Several scenario models in file")
            self.sc_model = parse_res["sc_model"][0]

    def run_simulation(self, translation = {}):
        """Run a simulation of the model"""
        # Get the Dempster-Shafer model
        if self.ds_model is None:
            raise ValueError("No Dempster-Shafer model")
        ds_model = self.ds_model.as_dempster_shafer()
        # Get the simulation scenario
        if self.sc_model is None:
            raise ValueError("No scenario model")
        scenario = self.sc_model
        if self.bh_model is not None:
            # If we have a behavior model, instantiate a BehaviorParser
            model = self.bh_model.as_bh_model(ds_model)
            if scenario.do_action_threshold is not None and scenario.no_action_threshold is not None:
                # Configure the necessity threshold if there are in the scenario file
                model.set_thresholds(scenario.do_action_threshold, scenario.no_action_threshold)
        else:
            # If there is no behavior model, use a Recorder model
            model = recorder_model.Recorder(ds_model)

        # Create the simulation
        simu = simulation.Simulation(model)
        events = []
        for evt in scenario.events:
            events.append(simulation.Event(evt.time, evt.what))
        simu.add_events(events)
        model.set_recorded(scenario.to_record)

        # Run the simulation
        simu.run()

        # Display the results
        model.display_recorded(translation)


    def __str__(self):
        rez = "Version: " + str(self.version) + "\n"
        rez += "Imports:\n"
        for imp in self.imports:
            rez += imp.uri + "\n"
        rez += "DS_Model: " + str(self.ds_model) + "\n"
        rez += "BH_Model: " + str(self.bh_model) + "\n"
        rez += "SC_Model: " + str(self.sc_model) + "\n"
        return rez


class IdefixParser:
    """The paser for Idefix model files"""
    model: Optional[Model] = None
    importsURI: set[str] = set()

    @staticmethod
    def process_import(parse_res: ParseResults) -> list[Import]:
        if parse_res["importURI"] not in IdefixParser.importsURI:
            IdefixParser.importsURI.add(parse_res["importURI"])
            imp_res = IdefixParser.load_import(parse_res["importURI"])
            return [Import(parse_res["importURI"], imp_res)]
        else :
            return []


    @staticmethod
    def process_timestamp(parse_res: ParseResults) -> datetime.datetime:
        timestamp = parse_res[0][0]
        date = datetime.datetime.min

        if "T" in parse_res[0][0]:
            date = datetime.datetime(year=int(timestamp[0:4]),
                                     month=int(timestamp[4:6]),
                                     day=int(timestamp[6:8]))
            timestamp = timestamp[9:]
        date += datetime.timedelta(hours=int(timestamp[0:2]),
                                   minutes=int(timestamp[2:4]),
                                   seconds=float(timestamp[4:]))
        return date

    @staticmethod
    def process_event(parse_res: ParseResults) -> Event:
        return Event(parse_res["time"], parse_res["observation"])

    @staticmethod
    def process_frac(parse_res: ParseResults) -> Fraction:
        return Fraction(parse_res[0])

    @staticmethod
    def process_massvalue(parse_res: ParseResults) -> dict[str, Any]:
        return {"diseases": parse_res["diseases"], "weight": parse_res["weight"] }

    @staticmethod
    def process_massfunc(parse_res: ParseResults) -> MassFunction:
        values = []
        for value in parse_res["massvalues"]:
            values.append((set(value["diseases"][0].asList()), value["weight"]))
        return MassFunction(set(parse_res["observations"]), values)

    @staticmethod
    def process_ds_model(parse_res: ParseResults) -> DSModel:
        return DSModel(parse_res["observations"], parse_res["diseases"], parse_res["masses"])

    @staticmethod
    def process_sc_model(parse_res: ParseResults) -> SCModel:
        torec = []
        no_act = None
        do_act = None
        if "to_record" in parse_res:
            for r in parse_res["to_record"][0]:
                torec.append(set(r))
        if "no_action" in parse_res:
            no_act = parse_res["no_action"]
        if "do_action" in parse_res:
            do_act = parse_res["do_action"]

        return SCModel(parse_res["events"], torec, no_act, do_act)

    @staticmethod
    def process_rule(parse_res: ParseResults) -> Rule:
        return Rule(parse_res["trigger"], parse_res["weight"], parse_res["action"])

    @staticmethod
    def process_bh_model(parse_res: ParseResults) -> BHModel:
        return BHModel(parse_res["hierarchy"], parse_res["rules"])

    @staticmethod
    def process_model(parse_res: ParseResults):
        if IdefixParser.model is None:
            IdefixParser.model = Model()
        IdefixParser.model.update(parse_res)
        return IdefixParser.model

    comment_pp = pp.Suppress('//') + pp.SkipTo(pp.LineEnd()).suppress()
    import_pp = pp.Keyword("import").suppress() + pp.QuotedString('"', escChar='\\')("importURI")
    import_pp.set_parse_action(process_import)

    observation_pp = pp.Word(pp.identchars)
    disease_pp = pp.Word(pp.identchars)

    obslist_pp = (observation_pp
                | (pp.Literal('[').suppress() + pp.DelimitedList(observation_pp, pp.Suppress(",")) + pp.Literal(']').suppress())
                 )
    diseaselist_pp = (disease_pp
                    | (pp.Literal('[').suppress() + pp.DelimitedList(disease_pp, pp.Suppress(",")) + pp.Literal(']').suppress())
                     )
    diseaselist_pp.set_parse_action(lambda pr : list((pr,)))  # Ensure lists of lists are not flattened

    frac_pp = pp.Combine(pp.Word(pp.nums) + pp.Opt('.' + pp.Word(pp.nums)))
    frac_pp.set_parse_action(process_frac)

    massvalue_pp = (pp.Literal("-").suppress() + (diseaselist_pp | pp.Keyword('_uncertain_'))("diseases")
                  + pp.Literal(':').suppress() + (frac_pp | pp.Keyword('_catch_'))("weight")
                   )
    massvalue_pp.set_parse_action(process_massvalue)

    mass_pp = (pp.Literal("-").suppress() + obslist_pp("observations")
                                          + pp.Literal("->").suppress() + pp.Literal('{').suppress()
                                          + pp.OneOrMore(massvalue_pp)("massvalues")
                                          + pp.Literal('}').suppress()
              )
    mass_pp.set_parse_action(process_massfunc)

    ds_model_pp = (pp.Keyword("ds_model:").suppress()
                 + pp.Keyword("observations:").suppress() + pp.OneOrMore(pp.Suppress('-') + observation_pp)("observations")
                 + pp.Keyword("diseases:").suppress() + pp.OneOrMore(pp.Suppress('-') + disease_pp)("diseases")
                 + pp.Keyword("masses:").suppress() + pp.OneOrMore(mass_pp)("masses")
                   )
    ds_model_pp.set_parse_action(process_ds_model)

    date_pp = pp.Combine((pp.Char(pp.nums) * 4)("year") + pp.Suppress("-")
                       + (pp.Char(pp.nums) * 2)("month") + pp.Suppress("-")
                       + (pp.Char(pp.nums) * 2)("day")
                        )
    time_pp = pp.Combine((pp.Char(pp.nums) * 2)("hours") + pp.Suppress(":")
                       + (pp.Char(pp.nums) * 2)("minutes") + pp.Suppress(":")
                       + ((pp.Char(pp.nums) * 2) + pp.Opt('.' + pp.Char(pp.nums)[1,3]))("seconds")
                        )

    timestamp_pp = pp.Combine(pp.Opt(date_pp + pp.Literal("T")) + time_pp)
    timestamp_pp.set_parse_action(process_timestamp)

    event_pp = timestamp_pp("time") + pp.Keyword(":").suppress() + observation_pp("observation")
    event_pp.set_parse_action(process_event)

    record_pp = pp.Keyword('record:').suppress() + pp.OneOrMore(pp.Suppress('-') + diseaselist_pp)
    record_pp.set_parse_action(lambda pr : list((pr,)))  # Ensure lists of lists are not flattened

    sc_model_pp = (
                    pp.Keyword("scenario:").suppress()
                  + pp.OneOrMore(event_pp)("events")
                  + pp.Opt(record_pp)("to_record")
                  + (pp.Opt(pp.Keyword("no_action_threshold:").suppress() + frac_pp("no_action"))
                   & pp.Opt(pp.Keyword("do_action_threshold:").suppress() + frac_pp("do_action"))
                    )
                  )
    sc_model_pp.set_parse_action(process_sc_model)

    concept_pp = pp.Word(pp.identchars)
    conceptlist_pp = (concept_pp
                    | (pp.Literal('[').suppress() + pp.DelimitedList(concept_pp, pp.Suppress(",")) + pp.Literal(']').suppress())
                     )
    conceptlist_pp.set_parse_action(lambda pr : list((pr,)))  # Ensure lists of lists are not flattened

    meaning_pp = (pp.Keyword("[*]")
               | (pp.Suppress("[") + pp.DelimitedList((concept_pp | disease_pp), pp.Suppress(",")) + pp.Suppress("]")))

    definition_pp = pp.Suppress("-") + concept_pp("concept") + pp.Suppress(":") + meaning_pp("meaning")
    definition_pp.set_parse_action(lambda pr : {pr["concept"]: pr["meaning"].asList()})

    rule_pp = pp.Suppress("-") + conceptlist_pp("trigger") + pp.Suppress("--(") + frac_pp("weight") + pp.Suppress(")->") + obslist_pp("action")
    rule_pp.set_parse_action(process_rule)

    bh_model_pp = (pp.Keyword("behavior:").suppress()
                 + pp.Opt(pp.Keyword("hierarchy:").suppress() + pp.OneOrMore(definition_pp))("hierarchy")
                 + pp.Keyword("rules:").suppress() + pp.OneOrMore(rule_pp)("rules"))
    bh_model_pp.set_parse_action(process_bh_model)

    model_pp = (pp.Keyword('idefix').suppress()
              + pp.QuotedString('"', escChar='\\')("version")
              + pp.ZeroOrMore(import_pp)("imports")
              + pp.Opt(ds_model_pp)("ds_model")
              + pp.Opt(bh_model_pp)("bh_model")
              + pp.Opt(sc_model_pp)("sc_model")
                )
    model_pp.set_parse_action(process_model)
    model_pp.ignore(comment_pp)

    @staticmethod
    def load_import(filename : str):
        with (io.open(filename, "r", encoding="utf-8") as idefixfile):
            model = IdefixParser.model_pp.parse_file(idefixfile, encoding="utf-8", parse_all=True)
            return model

    @staticmethod
    def load_model(filename : str):
        IdefixParser.model = IdefixParser.load_import(filename)[0]
        return IdefixParser.model

    @staticmethod
    def run_simulation(translation={}):
        if IdefixParser.model is None:
            print("Please load a model before running a simulation.")
        else:
            IdefixParser.model.run_simulation(translation)

if __name__ == "__main__":
    IdefixParser.load_model("pneumo_sc.ifx")
    print(IdefixParser.model)
    IdefixParser.run_simulation()
    IdefixParser.load_model("grippe_avc_sc.ifx")
    IdefixParser.run_simulation()
