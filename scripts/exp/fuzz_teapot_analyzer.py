#!/usr/bin/env python3
import sys
from pprint import pprint
from typing import Dict, Set, List, Tuple, Optional
from argparse import ArgumentParser
import subprocess
import re
import json
import time
from operator import itemgetter


class SaneJSONEncoder(json.JSONEncoder):
    def default(self, o):
        get_dict = getattr(o, "get_dict", None)
        if callable(get_dict):
            return get_dict()
        else:
            return o.__dict__


# ====================
# Data Collection
# ====================
class Fault:
    address: int
    accessed_addresses: Set[int]
    offsets: Set[int]
    branch_sequences: Set[Tuple[int]]
    order: int = 0
    fault_count: int = 0
    controlled: bool = False
    controlled_offset: bool = False
    types: Set[int]

    def __init__(self, address: int):
        self.address = address
        self.accessed_addresses = set()
        self.offsets = set()
        self.branch_sequences = set()
        self.types = set()

    def __lt__(self, other):
        return self.address < other.address

    def get_dict(self):
        sequences = []
        for seq in self.branch_sequences:
            sequences.append(list([hex(b) for b in seq]))

        return {
            "address": hex(self.address),
            "accessed_addresses": sorted(list([a for a in self.accessed_addresses])),
            "offsets": sorted(list([a for a in self.offsets])),
            "branch_sequences": sequences,
            "order": self.order,
            "fault_count": self.fault_count,
            "controlled": self.controlled,
            "controlled_offset": self.controlled_offset,
            "types": list(self.types)
        }

    def load(self, data: Dict):
        self.accessed_addresses = set([int(i) for i in data["accessed_addresses"]])
        self.offsets = set([int(i) for i in data["offsets"]])
        for branch_sequence in data["branch_sequences"]:
            self.branch_sequences.add(tuple([int(b, 16) for b in branch_sequence]))
        self.order = int(data["order"])
        self.fault_count = int(data["fault_count"])
        self.controlled = bool(data["controlled"])
        self.controlled_offset = bool(data["controlled_offset"])
        self.types = set([int(i) for i in data["types"]])

    def update(self, update):
        assert (self.address == update.address), \
            "Updated address does not match: {} and {}".format(self.address, update.address)

        # define controllability:
        # a fault is controllable if there is at least one experiment where the accessed addresses
        # or their offsets differ
        if update.accessed_addresses and self.accessed_addresses and \
                update.accessed_addresses != self.accessed_addresses:
            self.controlled = True
        if update.offsets and self.offsets and update.offsets != self.offsets:
            self.controlled_offset = True

        self.accessed_addresses |= update.accessed_addresses
        self.offsets |= update.offsets
        self.branch_sequences |= update.branch_sequences
        self.fault_count += 1
        self.types |= update.types


class Branch:
    address: int
    faults: Set[int]
    fault_count: int = 0
    nonspeculative_execution_count: int = 0

    def __init__(self, address):
        self.address = address
        self.faults = set()

    def __lt__(self, other):
        return self.address < other.address

    def get_dict(self):
        return {
            "address": hex(self.address),
            "faults": list([hex(f) for f in sorted(self.faults)]),
            "fault_count": self.fault_count,
            "nonspeculative_execution_count": self.nonspeculative_execution_count,
        }

    def load(self, data):
        self.faults = set([int(i, 16) for i in data["faults"]])
        self.fault_count = int(data["fault_count"])
        self.nonspeculative_execution_count = int(data["nonspeculative_execution_count"])

    def update(self, branch_update: 'Branch'):
        assert (self.address == branch_update.address)
        self.fault_count += 1
        self.faults |= branch_update.faults


class CollectedResults:
    total_guards: int
    branches: Dict[int, Branch]
    faults: Dict[int, Fault]
    crashed_runs: List[str]
    statistics: Dict

    def __init__(self):
        self.branches = {}
        self.faults = {}
        self.statistics = {}
        self.crashed_runs = []
        self.total_guards = 0

    def update(self, single_experiment_results: 'CollectedResults'):
        for edge_address, new_edge_data in single_experiment_results.branches.items():
            edge = self.branches.setdefault(edge_address, Branch(edge_address))
            edge.update(new_edge_data)

        for instruction_address, new_instruction_data in single_experiment_results.faults \
                .items():
            instruction = self.faults \
                .setdefault(instruction_address, Fault(instruction_address))
            instruction.update(new_instruction_data)

    def merge(self, full_data):
        for address, data in full_data["branches"].items():
            branch = self.branches.setdefault(int(address), Branch(int(address)))
            branch.nonspeculative_execution_count += data["nonspeculative_execution_count"]
            branch.fault_count += data["fault_count"]
            for f in data.get("faults", []):
                branch.faults.add(int(f, 16))

        for address, data in full_data["faults"].items():
            fault = self.faults.setdefault(int(address), Fault(int(address)))
            fault.fault_count += data["fault_count"]
            fault.order = data["order"] if fault.order == 0 or fault.order > data["order"] \
                else fault.order
            fault.controlled |= bool(data["controlled"])
            fault.controlled_offset |= bool(data["controlled_offset"])
            for a in data["accessed_addresses"]:
                fault.accessed_addresses.add(a)
            for a in data["offsets"]:
                fault.offsets.add(a)
            for a in data["types"]:
                fault.types.add(a)
            for branch_sequence in data["branch_sequences"]:
                fault.branch_sequences \
                    .add(tuple([int(b, 16) for b in branch_sequence]))

        for e in full_data["errors"]:
            self.crashed_runs.append(e)

    def get_dict(self):
        return {
            "errors": self.crashed_runs,
            "statistics": self.statistics,
            "branches": self.branches,
            "faults": self.faults,
        }

    def load(self, results_json: Dict):
        for key, data in results_json["branches"].items():
            branch = Branch(int(key))
            branch.load(data)
            self.branches[key] = branch

        for key, data in results_json["faults"].items():
            fault = Fault(int(key))
            fault.load(data)
            self.faults[key] = fault

        self.crashed_runs = results_json["errors"]
        self.statistics = results_json["statistics"]

    def collect_statistics(self):
        self.statistics = {
            "branches": len(self.branches),
            "faults": len(self.faults)
        }

    def set_order(self):
        for fault in self.faults.values():
            for branch_sequence in fault.branch_sequences:
                if fault.order == 0 or fault.order > len(branch_sequence):
                    fault.order = len(branch_sequence)

    def minimize_sequences(self):
        """Remove redundant branch sequences.
        E.g., if we have two sequences: (A, B, C) and (A, B, C, D),
        we consider the latter one redundant as the same vulnerability
        could be triggered by a misprediction of a subset of branches in it.
        """
        for fault in self.faults.values():
            # remove duplicates first and generate a nice list of sorted tuples
            sequences = set([tuple(set(s)) for s in fault.branch_sequences])

            # sort
            sequences = list(sequences)
            sequences.sort(key=lambda x: len(x), reverse=True)

            # search for supersets
            sequences_to_keep = []
            while len(sequences) > 0:
                top_sequence = sequences.pop()
                sequences_to_keep.append(top_sequence)

                not_supersets_of_top = []
                for other_sequence in sequences[:]:
                    # same length, different contents - definitely not a superset
                    # (duplicates are already removed)
                    if len(top_sequence) == len(other_sequence):
                        not_supersets_of_top.append(other_sequence)
                        continue

                    # check for supersets
                    # since the list is sorted, here len(other_sequence) > len(top_sequence)
                    for element in top_sequence:
                        if element not in other_sequence:
                            not_supersets_of_top.append(other_sequence)
                            break

                sequences = not_supersets_of_top

            fault.branch_sequences = set(sequences_to_keep)

        # after the minimization, some of the data in branches is not valid any more
        for branch in self.branches.values():
            branch.faults = set()

    def minimize_accessed_addresses(self):
        """Remove most of the data about accessed addresses
        and leave only the range limits
        """
        for fault in self.faults.values():
            accessed = list(fault.accessed_addresses)
            accessed.sort()
            redundant = []
            range_started = False
            for i in range(len(accessed) - 1):
                # end of a range
                if accessed[i + 1] - accessed[i] > 64:
                    range_started = False
                    continue

                # start of a range
                if not range_started:
                    range_started = True
                    continue

                # in a range
                redundant.append(accessed[i])
            fault.accessed_addresses -= set(redundant)


class Collector:
    results: CollectedResults
    current_experiment: CollectedResults
    main_branch: str
    log_timer: Optional[int] = None
    last_log: time
    out_file: str

    def __init__(self, output, log_timer=None):
        self.current_experiment = CollectedResults()
        self.results = CollectedResults()
        self.log_timer = log_timer
        self.last_log = time.time()
        self.out_file = output

    def collect_data(self, main_branch):
        self.main_branch = main_branch

        # connect to the SUT's output and process it, line by line
        while True:
            try:
                line = sys.stdin.readline()
            except UnicodeDecodeError:
                print("Cannot process non-unicode data.\n"
                      "Set the required encoding in the PYTHONIOENCODING environment variable")
                exit(1)

            if not line:
                break  # EOF
            if not self.process_line(line):
                break
        self.process_experiment()  # process the last experiment

        self.write_output(time.time())

    def process_line(self, line) -> bool:
        # check for errors
        if "Error" in line:
            self.results.crashed_runs.append(line)
            return False

        # if we start a new experiment, aggregate the previous one
        if line.startswith("[NaHCO3], Gadget Type"):
            self.process_experiment()
            return True

        # filter out the lines not produced by SpecFuzz
        if not line.startswith(r'[NaHCO3],'):
            return True

        # parse the line
        try:
            values = line.split(",")
            fault_type = values[1].strip()
            fault_address = int(values[2], 16)
            accessed_address = int(values[3], 16)
            tag = values[4].strip()
            offset = 0
            branches_sequence = [0] # Disabled
            #branches_sequence = [int(x, 16) for x in values[6:-1]]
        except:
            print("Error parsing string: " + str(line))
            return True

        if self.main_branch == "first":
            branch_address = branches_sequence[-1]
        else:
            branch_address = branches_sequence[0]

        # add the parsed data to the current experiment
        branch = self.current_experiment.branches. \
            setdefault(branch_address, Branch(branch_address))
        branch.faults.add(fault_address)

        fault = self.current_experiment.faults \
            .setdefault(fault_address, Fault(fault_address))
        if offset != 0:
            fault.offsets.add(offset)
        else:
            fault.accessed_addresses.add(accessed_address)
        fault.branch_sequences.add(tuple(sorted(branches_sequence)))
        fault.types.add(f"{fault_type} {tag}")
        return True

    def process_experiment(self):
        self.results.update(self.current_experiment)
        self.current_experiment.branches.clear()
        self.current_experiment.faults.clear()

        current_time = time.time()
        if self.log_timer and current_time - self.last_log > self.log_timer:
            self.last_log = current_time
            self.write_output(current_time)

    def write_output(self, timestamp):
        output = f"{self.out_file}_{int(timestamp)}.json"

        # process results
        self.results.collect_statistics()
        #self.results.minimize_sequences()

        with open(output, 'w') as out_file:
            json.dump(self.results, out_file, indent=2, cls=SaneJSONEncoder)


def merge_reports(inputs, output):
    merged = CollectedResults()

    for i in inputs:
        print("Merging " + i)
        with open(i, 'r') as in_file:
            merged.merge(json.load(in_file))

    # re-process results
    merged.collect_statistics()

    with open(output, 'w') as out_file:
        json.dump(merged, out_file, indent=2, cls=SaneJSONEncoder)


def minimize_report(input_, output):
    results = CollectedResults()

    print("Loading")
    with open(input_, 'r') as in_file:
        data = json.load(in_file)

    print("Processing data")
    results.load(data)
    results.set_order()

    results.minimize_sequences()
    results.minimize_accessed_addresses()

    print("Storing")
    with open(output, 'w') as out_file:
        json.dump(results, out_file, indent=2, cls=SaneJSONEncoder)




def main():
    parser = ArgumentParser(description='', add_help=False)
    subparsers = parser.add_subparsers(help='sub-command help', dest='subparser_name')

    # Data collection
    parser_collect = subparsers.add_parser('collect')
    parser_collect.add_argument(
        "-o", "--output",
        type=str,
        required=True
    )
    parser_collect.add_argument(
        "-m", "--main-branch",
        type=str,
        choices=["first", "last"],
        default="first"
    )
    parser_collect.add_argument(
        "-l", "--log-timer",
        type=int,
        default=None
    )

    parser_merge = subparsers.add_parser('merge')
    parser_merge.add_argument(
        "inputs",
        type=str,
        nargs="+"
    )
    parser_merge.add_argument(
        "-o", "--output",
        type=str,
        required=True
    )

    parser_minimize = subparsers.add_parser('minimize')
    parser_minimize.add_argument(
        "input",
        type=str,
    )
    parser_minimize.add_argument(
        "-o", "--output",
        type=str,
        required=True
    )

    args = parser.parse_args()

    # now, do the actual analysis
    if args.subparser_name == "collect":
        collector = Collector(args.output, args.log_timer)
        collector.collect_data(args.main_branch)
    elif args.subparser_name == "merge":
        merge_reports(args.inputs, args.output)
    elif args.subparser_name == "minimize":
        minimize_report(args.input, args.output)


if __name__ == '__main__':
    main()

