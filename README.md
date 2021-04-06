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

Also get the alignments for gold + silver:

```
python src/extract_alignment.py -i Neural_DRS/data/3.0.0/en/gold_silver/train.txt -o alignments/gold_silver.json
```

If you want to use lemmatization in the next step (recommended), install Spacy:

```
pip install spacy
python -m spacy download en_core_web_sm
```

## Fixing output

Now, we actually are going to fix the output. The SRL predictions need to follow a specific format. Also, there are important settings in src/drs_config.py, relating to which roles we never insert or replace. Please check if these make sense for your experiments as well.

I've added an example SRL file based on ELMo with predictions for the dev set. The script can take multiple files as input to make things easier. In the example I'll take a BERT-based model and two char-level models based on Marian and OpenNMT:

```
python src/replace_roles_by_srl.py -i Neural_DRS/output/pmb-3.0.0/en//dev/bert_only/output1.txt Neural_DRS/output/pmb-3.0.0/en/dev/best_marian/output1.txt Neural_DRS/output/pmb-3.0.0/en/dev/best_opennmt.txt -a alignments/gold.json alignments/gold_silver.json -r srl/srl_elmo_dev.json -l
```

Likely, you have a corresponding gold standard file and you want to do some more analysis. The main question of course being whether the Counter score went up. Just add the gold standard like this:

```
python src/replace_roles_by_srl.py -i Neural_DRS/output/pmb-3.0.0/en//dev/bert_only/output1.txt Neural_DRS/output/pmb-3.0.0/en/dev/best_marian/output1.txt Neural_DRS/output/pmb-3.0.0/en/dev/best_opennmt.txt -a alignments/gold.json alignments/gold_silver.json -r srl/srl_elmo_dev.json -l -g Neural_DRS/data/3.0.0/en/gold/dev.txt
```

This should print the Counter scores and some extra analysis about the replacements.
