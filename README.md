# Overview

This repo lets you (hopefully) improve the DRS output of your parser by using separate SRL predictions.

## Setup
Clone the repo and move to directory:

```
git clone https://github.com/RikVN/SRL-DRS 
cd SRL-DRS
```

I strongly suggest to create a Conda environment:

```
conda create -n srl-drs python=3.6
conda activate srl-drs
```

Then, clone the Neural_DRS repo and run the setup script

```
git clone https://github.com/RikVN/Neural_DRS
cd Neural_DRS
./src/setup.sh
cd ../
```

Important: I assume we work with the English part of PMB release 3.0.0.

## Generating alignments

As a first step, we create the alignments between tokens and DRS concepts:

```
mkdir alignments
python src/extract_alignment.py -i Neural_DRS/data/3.0.0/en/gold/train.txt -o alignments/gold.json
```

Also get the alignments for gold + silver + bronze:

```
python src/extract_alignment.py -i Neural_DRS/data/3.0.0/en/gold_silver_bronze/train.txt -o alignments/gold_silver_bronze.json
```

If you want to use lemmatization in the next step (recommended), install Spacy:

```
pip install spacy
python -m spacy download en_core_web_sm
```

## Fixing output

Now, we actually are going to fix the output. The SRL predictions need to follow a specific format. Also, there are important settings in src/drs_config.py, relating to which roles we never insert or replace. Currently these are fixed for the SRL files we have, needs to be fixed for a more general version.

I've added the SRL files with predictions for dev/test, with DRS-based and CCG-based conversion. The script can take multiple files as input to make things easier. In the example I'll take the best BERT-based model and two char-level models based on Marian and OpenNMT:

```
python src/replace_roles_by_srl.py -i Neural_DRS/output/pmb-3.0.0/en//dev/bert_char_sem_2enc/output1.txt Neural_DRS/output/pmb-3.0.0/en/dev/best_marian/output1.txt Neural_DRS/output/pmb-3.0.0/en/dev/best_opennmt.txt -a alignments/gold.json alignments/gold_silver_bronze.json -r srl/ccg_elmo.dev.json -l
```

The fixed output files are now in ${in_file}.fix.

Important: if you use the DRS-based SRL files, you have to use --reorder with the tokenized file.

```
python src/replace_roles_by_srl.py -i Neural_DRS/output/pmb-3.0.0/en//dev/bert_char_sem_2enc/output1.txt Neural_DRS/output/pmb-3.0.0/en/dev/best_marian/output1.txt Neural_DRS/output/pmb-3.0.0/en/dev/best_opennmt.txt -a alignments/gold.json alignments/gold_silver_bronze.json -r srl/ccg_elmo.dev.json -l --reorder Neural_DRS/data/3.0.0/en/gold/dev.txt.raw.tok.gold
```

But this didn't print any scores yet. Likely, you have a corresponding gold standard file and you want to do some more analysis. The main question of course being whether the Counter score went up. Just add the gold standard like this:

```
python src/replace_roles_by_srl.py -i Neural_DRS/output/pmb-3.0.0/en//dev/bert_char_sem_2enc/output1.txt Neural_DRS/output/pmb-3.0.0/en/dev/best_marian/output1.txt Neural_DRS/output/pmb-3.0.0/en/dev/best_opennmt.txt -a alignments/gold.json alignments/gold_silver_bronze.json -r srl/ccg_elmo.dev.json -l -g Neural_DRS/data/3.0.0/en/gold/dev.txt
```

This should print the Counter scores and some extra analysis about the replacements.
