import argparse
import csv
import json
from random import shuffle
import re
from os.path import join, splitext
from os import listdir
import sys


CHUNK_DIR = "chunks"
TARGET_TRAIN_FILE = "nwbib_subjects_train.tsv"
TARGET_EVAL_FILE = "nwbib_subjects_eval.tsv" 
TARGET_NO_SUBJECTS_FILE = "nwbib_unindexed_titles.txt"

SKOS_VOCAB_TERMS = None

ARGS_HELP_STRINGS = {
    "stats": "Prints statistical information on all processed NWBib data",
    "vocabulary": ("Add a path to the NWBib SKOS vocabulary file "
                   "(https://github.com/hbz/lobid-vocabs/blob/master/nwbib/nwbib.ttl). "
                   "All NWBib subjects will be tested against the vocabulary "
                   "and excluded if not found."),
    "percentage_eval_data": ("A float between 0.0 and 1.0 which determines the percentage "
                             "of extracted data to be redirected to the eval file. Defaults "
                             "to 0.1"),
    "eval_data_starting_index": ("An int value which correlates to a record index in the NWBib "
                                 "data. If set, the eval data will be extract continuously "
                                 "from this record on until the desired percentage of eval "
                                 "data is reached. If not set, eval data will be sampled "
                                 "at random.")
}

def extract_data(record):
    ret = {
        'title': '',
        'otherTitleInformation': '',
        'subjects': []
    }
    ret['title'] = record.get('title', '')
    if 'otherTitleInformation' in record:
        ret['otherTitleInformation'] = ', '.join(record['otherTitleInformation'])
    subjects = record.get('subject', [])
    for subject_dict in subjects:
        source_id = subject_dict.get("id", '')
        if source_id.startswith("https://nwbib.de/subjects"):
            label = subject_dict.get("label", '')
            if SKOS_VOCAB_TERMS is None:
                ret["subjects"].append((source_id, label))
            else:
                if source_id in SKOS_VOCAB_TERMS:
                    ret["subjects"].append((source_id, label))
                else:
                    msg = 'Warning: Subject {} ({}) not found in provided SKOS vocabulary - skipping'
                    print(msg.format(source_id, label))
    return ret

def _extract_voc_terms(voc_file_path):
    global SKOS_VOCAB_TERMS
    term_id_pattern = re.compile("^:(?P<term_id>N[0-9]+)$")
    SKOS_VOCAB_TERMS = []
    with open(voc_file_path) as voc:
        for line in voc:
            match = term_id_pattern.match(line)
            if match:
                term = "https://nwbib.de/subjects#" + match.group("term_id")
                SKOS_VOCAB_TERMS.append(term)

def _prepare_tsv_data(record):
    combined_title = record["title"] if not record["otherTitleInformation"] else record["title"] + " - " + record["otherTitleInformation"]
    subjects = ["<" + subject_tup[0] + ">" for subject_tup in record["subjects"]]
    line = [combined_title] + subjects
    return line

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--stats", action="store_true",
                        help=ARGS_HELP_STRINGS["stats"])
    parser.add_argument("-v", "--vocabulary",
                        help=ARGS_HELP_STRINGS["vocabulary"])
    parser.add_argument("-p", "--percentage_eval_data", type=float, default=0.1,
                        help=ARGS_HELP_STRINGS["percentage_eval_data"])
    parser.add_argument("-t", "--eval_data_starting_index", type=int,
                        help=ARGS_HELP_STRINGS["eval_data_starting_index"])
    args = parser.parse_args()
    
    if args.percentage_eval_data > 1.0 or args.percentage_eval_data < 0.0:
        print("ERROR: Eval data percentage must be a value between 0.0 and 1.0!")
        sys.exit()
    
    if args.vocabulary:
        _extract_voc_terms(args.vocabulary)

    total_records = 0
    record_keys_distribution = {}
    subjects_per_record_distribution = {}
    subjects_distribution = {}
    
    valid_records = []
    records_without_subjects = []

    for filename in listdir(CHUNK_DIR):
        path = join(CHUNK_DIR, filename)
        with open(path) as f:
            content = f.read()
            try:
                json_dicts = json.loads(content)
            except json.decoder.JSONDecodeError as jsond:
                print("Could not read from file {}: {}".format(path, jsond))
                continue
            for record in json_dicts:
                for key in record.keys():
                    if key not in record_keys_distribution:
                        record_keys_distribution[key] = 1
                    else:
                        record_keys_distribution[key] += 1
                data = extract_data(record)
                if data["subjects"]:
                    valid_records.append(data)
                else:
                    records_without_subjects.append(data)
                total_records += 1
                if len(valid_records) % 100000 == 0:
                    print(str(len(valid_records)) + " valid records extracted")
                num_subjects = len(data["subjects"])
                if num_subjects not in subjects_per_record_distribution:
                    subjects_per_record_distribution[num_subjects] = 1
                else:
                    subjects_per_record_distribution[num_subjects] += 1
                for subject_tup in data["subjects"]:
                    stats_key = subject_tup[0] + " (" + subject_tup[1] + ")"
                    if stats_key not in subjects_distribution:
                        subjects_distribution[stats_key] = 1
                    else:
                        subjects_distribution[stats_key] += 1
                
        #print(json.dumps(json_dicts[100], indent = 2))
        #print(json_dicts[100].keys())
    print("Total NWBIB records: " + str(total_records))
    print("Subject count distribution: ")
    print(json.dumps(subjects_per_record_distribution, indent = 2, sort_keys = True))
    print(json.dumps(record_keys_distribution, indent = 2, sort_keys = True))
    print(json.dumps(subjects_distribution, indent = 2, sort_keys = True))
    
    num_eval_records = round(len(valid_records) * args.percentage_eval_data)
    msg = "{} valid records extracted from NWBib file, {} ({}%) will be reserved for the eval file." 
    print(msg.format(len(valid_records), num_eval_records, args.percentage_eval_data * 100))

    if args.eval_data_starting_index:
        if args.eval_data_starting_index > (len(valid_records) - 1):
            msg = "ERROR: Starting index is out of bounds ({}, but only {} valid records could be extracted)."
            print(msg.format(args.eval_data_starting_index, len(valid_records)))
            sys.exit()
        ending_index = args.eval_data_starting_index + num_eval_records
        if ending_index > (len(valid_records) - 1):
            ending_index = len(valid_records) - 1
            msg = "WARNING: Starting index is too high, can only extract {} valid records before end of file is reached."
            print(msg.format(ending_index - args.eval_data_starting_index))
        msg = "Records from index {} to {} will be reserved as eval data."
        print(msg.format(args.eval_data_starting_index, ending_index))
        eval_indexes = range(args.eval_data_starting_index, ending_index) 
    else:
        msg = "No starting index given, {} eval records will be select at random"
        print(msg.format(num_eval_records))
        all_indexes = list(range(len(valid_records)))
        shuffle(all_indexes)
        eval_indexes = all_indexes[:num_eval_records]
        eval_indexes.sort()

    training_records = []
    eval_records = []
    for i in range(len(valid_records)):
        if  eval_indexes and eval_indexes[0] == i:
            eval_records.append(valid_records[i])
            eval_indexes.pop(0)
            print(eval_indexes[:10])
        else:
            training_records.append(valid_records[i])
    
    with open(TARGET_TRAIN_FILE, "w") as ttf:
        writer = csv.writer(ttf, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for record in training_records:
            writer.writerow(_prepare_tsv_data(record))
    with open(TARGET_EVAL_FILE, "w") as ttf:
        writer = csv.writer(ttf, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for record in eval_records:
            writer.writerow(_prepare_tsv_data(record))
    with open(TARGET_NO_SUBJECTS_FILE, "w") as tnsf:
        for record in records_without_subjects:
            combined_title = record["title"] if not record["otherTitleInformation"] else record["title"] + " - " + record["otherTitleInformation"]
            tnsf.write(combined_title + "\n")

if __name__ == '__main__':
    main()
