# From here we import locations, such as for counter and referee
main_fol = ''
counter= main_fol + 'Neural_DRS/DRS_parsing/evaluation/counter.py'
sig_file = main_fol + 'Neural_DRS/DRS_parsing/evaluation/clf_signature.yaml'
# Config settings of experiment
never_replace_roles = ["V", "Time", "Name"]
never_replace_concs = ["person", "be", "entity"]
# Based on precision of SRL parser
never_insert_roles =  { "drs_elmo": ["Attribute", "Goal", "Product"], "drs_glove": ["Goal", "Product", "Topic"], "ccg_elmo" : ["Attribute", "Goal"], "ccg_glove" : ["Attribute", "Goal"]}
