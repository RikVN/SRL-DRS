#!/usr/bin/env python
# -*- coding: utf8 -*-

'''
Extract from the gold standard which tokens align with which DRS concepts
'''

import argparse
from collections import Counter
from Neural_DRS.src.uts import get_drss, is_concept, save_json_dict


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_file", required=True, type=str,
                        help="Input file with DRSs")
    parser.add_argument("-o", "--output_file", required=True, type=str,
                        help="Output file (JSON) with alignment info")
    args = parser.parse_args()
    return args


def get_alignment_token(string):
    '''From a clause string in a DRS, get the token that is aligned'''
    between_quotes = False
    for idx, char in enumerate(string):
        if char == '"':
            between_quotes = not between_quotes
        # We found the comment character, simply add the rest
        elif char == '%' and not between_quotes:
            return string[idx+1:].strip()
    # No comment found, return empty string
    return ''


def main():
    '''Main function'''
    args = create_arg_parser()
    drss = get_drss(args.input_file)
    align_dict = {}
    for drs in drss:
        for clause in drs:
            # Only select non-comments and clauses that are of the concept type
            if not clause.strip().startswith('%') and is_concept(clause.strip().split()[1]):
                align = get_alignment_token(clause)
                concept = clause.strip().split()[1]
                # There can be multiple alignments, save them all
                if align.strip():
                    for tok in align.split():
                        if not tok.startswith('['):
                            # Save in dictionary
                            if concept in align_dict:
                                align_dict[concept].append(tok.lower())
                            else:
                                align_dict[concept] = [tok.lower()]

    # Fix the list to order them based on frequency, we prefer frequent alignment over infrequent
    new_dict = {}
    for key in align_dict:
        new_dict[key] = [k for k, _ in Counter(align_dict[key]).most_common()]
    # Now dump the JSON dict to output file
    save_json_dict(new_dict, args.output_file)


if __name__ == "__main__":
    main()
