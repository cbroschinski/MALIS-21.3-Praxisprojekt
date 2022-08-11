import argparse
import csv
import json
from os.path import join, splitext
from os import listdir


CHUNK_DIR = "chunks"
TARGET_TRAIN_FILE = "nwbib_subjects_train.tsv"
TARGET_TEST_FILE = "nwbib_subjects_test.tsv" 

ARGS_HELP_STRINGS = {
    "stats": "Prints statistical information on all processed NWBib data"
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
            ret["subjects"].append((source_id, label))
    return ret

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--stats", action="store_true",
                        help=ARGS_HELP_STRINGS["stats"])
    args = parser.parse_args()

    total_records = 0
    record_keys_distribution = {}
    subjects_per_record_distribution = {}
    subjects_distribution = {}
    
    records = []

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
                records.append(data)
                total_records += 1
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
        if len(records) % 100000 == 0:
            print(str(len(records)) + " records processed")
    print("Total NWBIB records: " + str(total_records))
    print("Subject count distribution: ")
    print(json.dumps(subjects_per_record_distribution, indent = 2, sort_keys = True))
    print(json.dumps(record_keys_distribution, indent = 2, sort_keys = True))
    print(json.dumps(subjects_distribution, indent = 2, sort_keys = True))
    
    with open(TARGET_TRAIN_FILE, "w") as ttf:
        writer = csv.writer(ttf, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for record in records:
            if not record["subjects"]:
                continue
            combined_title = record["title"] if not record["otherTitleInformation"] else record["title"] + " - " + record["otherTitleInformation"]
            subjects = ["<" + subject_tup[0] + ">" for subject_tup in record["subjects"]]
            line = [combined_title] + subjects
            writer.writerow(line)

if __name__ == '__main__':
    main()
