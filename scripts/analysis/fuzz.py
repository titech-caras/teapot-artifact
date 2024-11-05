#!/usr/bin/env python3

import os
import pathlib
import glob
import re
import json
import csv
import sys
from collections import defaultdict

TAG_ATTACKER = 0x1
TAG_ATTACKER_INDIRECT = 0x2
TAG_SECRET = 0x10
TAG_SECRET_INDIRECT = 0x20


def categorize_gadget(t):
    type_id, type_name, tag = t.split()
    suffix = type_name.replace('KASPER_', '')
    tag = int(tag, 16)

    if tag & (~0x33) != 0:
        return 'UNKNOWN'

    if type_name == 'KASPER_MDS':
        prefix = 'USER' if tag & TAG_ATTACKER else 'MASSAGE' if tag & TAG_ATTACKER_INDIRECT else 'UNKNOWN'
    else:
        prefix = 'USER' if tag & TAG_SECRET else 'MASSAGE' if tag & TAG_SECRET_INDIRECT else 'UNKNOWN'

    return prefix + '-' + suffix



def main():
    results = {}
    workspace_path = pathlib.Path(__file__).parent.parent.parent.resolve()

    teapot_result_files = glob.glob(os.path.join(workspace_path, 'results/fuzz/teapot/*.json'))
    specfuzz_result_files = glob.glob(os.path.join(workspace_path, 'results/fuzz/specfuzz/*.json'))
    
    for file_name in teapot_result_files:
        program_name = re.search(r'/([^/]*?)\.json', file_name)[1]
        gadget_counts = defaultdict(int)

        with open(file_name, 'r') as f:
            result = json.loads(f.read())
            for v in result['faults'].values():
                gadget_types = set([categorize_gadget(t) for t in v['types']])
                for t in gadget_types:
                    gadget_counts[t] += 1
        
        results[program_name] = gadget_counts

    for file_name in specfuzz_result_files:
        program_name = re.search(r'/([^/]*?)\.json', file_name)[1]
        if program_name not in results:
            print(f"Warning: Teapot result file for {program_name} not found", file=sys.stderr)
            continue

        with open(file_name, 'r') as f:
            result = json.loads(f.read())
            results[program_name]['SpecFuzz'] = int(result['statistics']['faults'])

    with open('results/fuzz_aggregated.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['Program Name', 'SpecFuzz (Reproduced)', 
                         'User-MDS', 'User-Cache', 'User-Port', 
                         'Massage-MDS', 'Massage-Cache', 'Massage-Port'])

        for k, v in sorted(results.items()):
            writer.writerow([k, v['SpecFuzz'], v['USER-MDS'], v['USER-CACHE'], v['USER-PORT'],
                             v['MASSAGE-MDS'], v['MASSAGE-CACHE'], v['MASSAGE-PORT']])



if __name__ == '__main__':
    main()
