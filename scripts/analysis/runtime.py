#!/usr/bin/env python3

import os
import pathlib
import glob
import re
import json
import csv


def main():
    results = {}
    workspace_path = pathlib.Path(__file__).parent.parent.parent.resolve()

    runtime_result_files = glob.glob(os.path.join(workspace_path, 'results/runtime/*.json'))
    for file_name in runtime_result_files:
        program_name = re.search(r'/([^/]*?)\.json', file_name)[1]
        with open(file_name, 'r') as f:
            result = json.loads(f.read())
            results[program_name] = result

    with open('results/runtime_aggregated.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['Program Name', 'Original', 'Teapot', 'SpecFuzz'])

        for k, v in sorted(results.items()):
            writer.writerow([k, v['original'], v['teapot'], v['specfuzz']])

if __name__ == '__main__':
    main()