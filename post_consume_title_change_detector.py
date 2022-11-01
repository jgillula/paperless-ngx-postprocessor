#!/usr/bin/env python3

import hashlib
import os
from pathlib import Path
from paperlessngx_postprocessor import Config, PaperlessAPI

if __name__ == "__main__":
    document_id = os.environ["DOCUMENT_ID"]

    filename = ""
    with open(os.environ["DOCUMENT_SOURCE_PATH"], "rb") as the_file:
        read_file = the_file.read()
        filename = "." + hashlib.sha256(read_file).hexdigest()
    
    old_filename = None
    with open(filename, "r") as title_file:
        old_filename = title_file.read()

    new_filename = Path(os.environ["DOCUMENT_SOURCE_PATH"]).name
    if old_filename != new_filename:
        config = Config()
        api = PaperlessAPI(config["paperless_api_url"],
                           auth_token = config["auth_token"],
                           paperless_src_dir = config["paperless_src_dir"])

        tag_id = api.get_item_id_by_name("tags", "Title Changed")
        document = api.get_document_by_id(os.environ["DOCUMENT_ID"])
        document["tags"].append(tag_id)
        api.patch_document(os.environ["DOCUMENT_ID"], {"tags": document["tags"],
                                                       "created_date": document["created_date"]})
    
    os.remove(filename)

