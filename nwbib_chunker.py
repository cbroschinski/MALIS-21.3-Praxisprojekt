import json
import os

# A small script to partition the nwbib JSON file into smaller chunks, since trying to process the whole 2GB file at once will probably run into memory issues. 
# A full NWBib snapshot can be obtained via
#
# curl --header "Accept-Encoding: gzip" "http://lobid.org/resources/search?q=inCollection.id%3A%22http%3A%2F%2Flobid.org%2Fresources%2FHT014176012%23%21%22&format=jsonl" > nwbib.gz
#
# gunzip it, then run this script to create the chunks
#

CHUNK_SIZE = 1000

f = open("nwbib")
if not os.path.isdir("chunks"):
    os.mkdir("chunks")
total_records = 0
records_in_chunk = 0
current_chunk_file = None
record = f.readline()
while record != '':
    if not current_chunk_file:
        current_chunk_file = "chunks/nwbib_" + str(total_records) + ".json"
        handle = open(current_chunk_file, "a")
        handle.write('[')
    handle.write(record)
    records_in_chunk += 1
    total_records += 1
    record = f.readline()
    if records_in_chunk >= CHUNK_SIZE or record == '':
        handle.write(']')
        handle.close()
        current_chunk_file = None
        records_in_chunk = 0
    else:
        handle.write(',')
    

# with open("nwbib.json") as f:
    # content = f.read()
    # count = 0
    # for line in content:
        # print(line)
        # count += 1
        # if count > 100:
            # break
        
