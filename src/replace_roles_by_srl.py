#!/usr/bin/env python
# -*- coding: utf8 -*-

'''
Replace script: decide here which roles in the DRS we replace by roles in the SRL data
'''

import os
import argparse
import subprocess
from Neural_DRS.src.uts import get_drss, is_concept, load_json_dict, json_by_line, is_role
from Neural_DRS.src.uts import between_quotes, write_list_of_lists, add_to_dict, average_list
from Neural_DRS.src.uts import read_matching_nonmatching_clauses, delete_if_exists
from drs_config import never_replace_roles, never_replace_concs, never_insert_roles, counter, sig_file


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_files", required=True, nargs="+",
                        help="Input files with DRSs we will try to fix by using SRL roles")
    parser.add_argument("-a", "--align_files", required=True, nargs="+",
                        help="Files with DRS alignments we will use")
    parser.add_argument("-r", "--role_file", required=True, type=str,
                        help="Input file with SRL information in JSON format")
    parser.add_argument("-o", "--output_ext", default=".fix", type=str,
                        help="Extension added to gold file to create output file")
    parser.add_argument("-g", "--gold_file", default='', type=str,
                        help="Gold standard file, if added we immediately run counter")
    parser.add_argument("-l", "--lemmatize", action="store_true",
                        help="Lemmatize using Spacy")
    args = parser.parse_args()
    return args


def figure_out_key(srl_data):
    '''Key for SRL is either "srl" or "predicted_srl"'''
    if "predicted_srl" in srl_data[0]:
        return "predicted_srl"
    if "srl" in srl_data[0]:
        return "srl"
    raise ValueError('"srl" and "predicted_srl" both not present in SRL data keys')


def run_counter(pred_file, gold_file, string):
    '''Run Counter for two files, print output to screen'''
    counter_call = 'python {0} -f1 {1} -f2 {2} -g {3}'.format(counter,
                                                              pred_file, gold_file, sig_file)
    output = subprocess.check_output(counter_call, shell=True).decode('utf-8')
    f_score = [x.strip().split()[-1] for x in output.split('\n') if x.startswith('F-score')][0]
    fixed_f = float(f_score) * 100
    print("{0} F-score: {1}".format(string, round(fixed_f, 1)))
    return fixed_f


def run_matching_counter(pred_file, gold_file):
    '''Run Counter with detailed clause matching and return the matching and non-matching clause
       in a list. We already have a function that can take an input file, so use that'''
    if not os.path.isfile('tmp.txt'):
        counter_call = 'python {0} -f1 {1} -f2 {2} -g {3} -prin -ms > tmp.txt' \
                       .format(counter, pred_file, gold_file, sig_file)
        subprocess.call(counter_call, shell=True)
    counter_list = read_matching_nonmatching_clauses('tmp.txt')
    # Clean up tmp file
    delete_if_exists('tmp.txt')
    return counter_list


def remove_after_char(string, remove_char):
    '''Remove all characters after certain char, except if between quotes'''
    between_quotes = False
    new_string = ''
    for char in string:
        if char == '"':
            between_quotes = not between_quotes
        elif char == remove_char and not between_quotes:
            return new_string
        new_string += char
    return new_string


def get_var_concepts(drs):
    '''Save which variables are paired with what concepts'''
    var_conc = {}
    for clause in drs:
        if is_concept(clause.split()[1]):
            var_conc[clause.split()[3]] = clause.split()[1]
    return var_conc


def read_srl_sents_and_roles(srl, srl_key):
    '''Read the SRL sentences and roles, extracting only relevant information'''
    srl_list = []
    for idx, role_list in enumerate(srl[srl_key]):
        # For predicted_srl it isn't a list of list of lists, but just a list of lists
        # This works for the current SRL output files of Tanja
        for values in role_list:
            if values[3] not in never_replace_roles:
                # Save information as role_dic[("accept", "I")] = "Agent"
                srl_list.append([srl["sentences"][idx][values[0]].lower(),
                                 srl["sentences"][idx][values[1]].lower(), values[3]])
    return srl_list


def clean_drs(drs):
    '''Remove comments from DRS and remove comment-only lines'''
    new_drs = []
    for clause in drs:
        if clause.strip().startswith('%'):
            continue
        new_drs.append(remove_after_char(clause.strip(), '%').strip())
    return new_drs


def match_tokens_concepts(align_sets, conc, tok, nlp):
    '''Match a concept to a token by using the alignments'''
    # For a full string match, always return true
    if conc == tok:
        return True

    # If specified, also lemmatize the token and check for that
    # Do the same thing for the concept, you never know what the model predicted
    if nlp:
        conc_lemma = [tk.lemma_ for tk in nlp(conc)][0]
        tok_lemma = [tk.lemma_ for tk in nlp(tok)][0]
        # Return a match if either combination matches
        if conc_lemma == tok_lemma or conc_lemma == tok or tok_lemma == conc:
            return True

    # Else use the alignments to find matches
    for align_set in align_sets:
        if conc in align_set:
            if tok in align_set[conc]:
                # We have a match: the token matches with this concept
                return True
    return False


def get_roles_per_box(drs):
    '''For each box, save which roles occur'''
    role_dict = {}
    for clause in drs:
        if is_role(clause.split()[1]):
            box = clause.split()[0]
            if box in role_dict:
                role_dict[box].append(clause.split()[1])
            else:
                role_dict[box] = [clause.split()[1]]
    return role_dict


def replace_by_srl(drs, srl, align_sets, srl_key, nlp, match_info, stats):
    '''Main function in which we possibly replace an output role by a predicted role'''
    # First we save which variables introduced which concepts and the tokens
    var_conc = get_var_concepts(drs)
    srl_list = read_srl_sents_and_roles(srl, srl_key)
    # Get the roles per box
    roles_per_box = get_roles_per_box(drs)

    # If we added a gold standard we also check if we replaced a previously already matched clause
    matched_clauses = [remove_after_char(in_str, '%').split('|')[0].strip() for in_str in match_info[0]] if match_info else []
    # Loop SRL role we possibly want to insert somewhere
    replace = {}
    for tok1, tok2, new_role in srl_list:
        # Check if we even plan to insert the role anyway
        if new_role not in never_insert_roles:
            for idx, clause in enumerate(drs):
                ident = clause.split()[1]
                # Only check roles that are different from to-be-inserted role
                if is_role(ident) and ident not in never_replace_roles and ident != new_role:
                    var1, role, var2, var3 = clause.split()
                    # If the role we want to insert (new_role) already exists in this box, do nothing
                    if var1 not in roles_per_box or new_role not in roles_per_box[var1]:
                        # For now, don't replace roles that have arguments between quotes
                        if not between_quotes(var2) and not between_quotes(var3):
                            # We have a predicted role that could potentially be replaced with the SRL role
                            # Get the two concepts that go along with it
                            # It is possible for predicted DRSs that a role variable does not have a
                            # corresponding concept, ignore that role as well then
                            if var2 in var_conc and var3 in var_conc:
                                # Also filter out combinations with too general concepts
                                if var_conc[var2] not in never_replace_concs \
                                   and var_conc[var3] not in never_replace_concs:
                                    # Now for the most important step: use the alignments that are extracted
                                    # from the training data to see if we can match concepts and tokens
                                    match1 = match_tokens_concepts(align_sets, var_conc[var2], tok1, nlp)
                                    match2 = match_tokens_concepts(align_sets, var_conc[var3], tok2, nlp)

                                    # If we found two matches, we save this as a possible replace
                                    if match1 and match2:
                                        matched = 1 if clause in matched_clauses else 0
                                        # Save clause index that needs to be changed and the role we swap in
                                        replace[idx] = new_role
                                        # Save some statistics here as well
                                        stats.append([role, new_role, tok1, tok2, var_conc[var2], var_conc[var3], matched])
    # We have a list of replacements, now do them
    new_drs = []
    for idx, clause in enumerate(drs):
        if idx in replace:
            var1, role, var2, var3 = clause.split()
            new_drs.append(" ".join([var1, replace[idx], var2, var3]))
        else:
            new_drs.append(clause)
    return new_drs, stats


def find_matching_idx(item, full_list):
    '''Return idx for first matching item in a full list'''
    for idx, value in enumerate(full_list):
        if item == value:
            return idx
    raise ValueError("No match found")


def order_by_freq(stats, idx_list):
    '''Calculate simple statistics for a certain idx in stats'''
    match_dic = {}
    total_dic = {}
    # Save match and total in their own dict
    for stat in stats:
        for idx in idx_list:
            total_dic = add_to_dict(total_dic, stat[idx])
            if stat[-1] == 1:
                match_dic = add_to_dict(match_dic, stat[idx])
    # Now sort the dictionary based on total
    min_value = 5
    res_list = []
    for w in sorted(total_dic, key=total_dic.get, reverse=True):
        num_matches = match_dic[w] if w in match_dic else 0
        if total_dic[w] >= min_value:
            res_list.append("{0}: {1}/{2}".format(w, total_dic[w] - num_matches, total_dic[w]))
    return res_list


def analyse_replacements(stats):
    '''Print statistics of the replacements, given that we know if they matched or not
       Stats contains: [old_role, new_role, token1, token2, concept1, concept2, match (0 or 1)]'''
    # First print basic stats for each role, token, concept, ordered by if they matched
    replaced_match = len([x for x in stats if x[-1] == 1])
    print ("Total replacements of matching clauses: {0}\n".format(replaced_match))
    headers = ["old roles", "new roles", "tokens", "concepts"]
    for idx in [0, 1]:
        out_list = order_by_freq(stats, [idx])
        print ("\nNumber of perhaps succesful replacements of {0}:".format(headers[idx]))
        for string in out_list:
            print (string)

    # For tokens and concepts we take them together
    for i, idx_list in enumerate([[2, 3], [4, 5]]):
        out_list = order_by_freq(stats, idx_list)
        print ("\nNumber of perhaps succesful replacements of {0}:".format(headers[i+2]))
        for string in out_list:
            print (string)


def replace_srl_for_file(input_file, srl_data, srl_key, align_sets, gold_file, stats, nlp, output_file):
    '''Most important function: replace SRL for a given input file'''
    drss = [clean_drs(drs) for drs in get_drss(input_file)]
    counter_list = run_matching_counter(input_file, gold_file) if gold_file else []

    # Loop over DRSs and see if we want to replace by a predicted role
    fixed_drss = []
    for idx, (drs, srl) in enumerate(zip(drss, srl_data)):
        counter_idx = counter_list[idx] if counter_list else []
        fixed_drs, stats = replace_by_srl(drs, srl, align_sets, srl_key, nlp, counter_idx, stats)
        fixed_drss.append(fixed_drs)

    # Write new DRSs to output file
    write_list_of_lists(fixed_drss, output_file)

    # Run Counter if we added a gold standard
    if gold_file:
        print ("\nScores for {0}".format(input_file))
        old_f = run_counter(input_file, gold_file, "Old")
        new_f = run_counter(output_file, gold_file, "New")
        diff = round(new_f - old_f, 2)
        print("Diff: {0}".format(diff))
        return stats, diff
    return stats, 0


def main():
    '''Main function of script'''
    args = create_arg_parser()
    if args.lemmatize:
        # Only import if necessary
        import spacy

    # Read in SRL data and align data sets
    srl_data = json_by_line(args.role_file)
    srl_key = figure_out_key(srl_data)
    align_sets = [load_json_dict(align_file) for align_file in args.align_files]

    # If we do lemmatization load spacy here, else just set to False
    nlp = spacy.load("en_core_web_sm") if args.lemmatize else False

    # Do the actual replacing here, save stats for multiple files perhaps
    # If we added a gold file, do some analysis on what type of clauses were correctly changed
    stats = []
    diffs = []
    before_rep = 0
    for input_file in args.input_files:
        before_rep = len(stats)
        stats, diff = replace_srl_for_file(input_file, srl_data, srl_key, align_sets, args.gold_file,
                                           stats, nlp, input_file + args.output_ext)
        diffs.append(diff)
        pr_str = "" if args.gold_file else ' ' + input_file
        print ("Total replacements{0}: {1}\n".format(pr_str, len(stats) - before_rep))

    # Print average improvement (or not)
    if args.gold_file:
        # Print statistics over the output of multiple files
        analyse_replacements(stats)
        print ("Average improvement over {0} files: {1}".format(len(args.input_files), average_list(diffs)))

if __name__ == "__main__":
    main()
