#!/usr/bin/env python3

import os
from pathlib import Path
import hashlib
#import magic
#import tempfile
#import subprocess

if __name__ == "__main__":
    filename = ""

    # mime = magic.Magic(mime=True)
    # mime_type = mime.from_file(os.environ["DOCUMENT_SOURCE_PATH"])
    # if os.environ["DOCUMENT_SOURCE_PATH"][-3:].lower() == "pdf" and mime_type != "application/pdf":
    #     print("Redoing pdf to get the right mime-type")
    #     with tempfile.TemporaryDirectory() as tmp_dir:
    #         temp_filename = os.path.join(tmp_dir, "tmp.pdf")
    #         subprocess.run(("qpdf", os.environ["DOCUMENT_SOURCE_PATH"], temp_filename))
    #         os.replace(temp_filename, os.environ["DOCUMENT_SOURCE_PATH"])
    # else:
    #     print(f"Mime_type of {os.environ['DOCUMENT_SOURCE_PATH']} was {mime_type}")
                       
    with open(os.environ["DOCUMENT_SOURCE_PATH"], "rb") as the_file:
        read_file = the_file.read()
        filename = "." + hashlib.sha256(read_file).hexdigest()
    #print("preconsume is " + hashlib.sha256(os.environ["DOCUMENT_SOURCE_PATH"])
    document_source_path = Path(os.environ["DOCUMENT_SOURCE_PATH"])
    with open(filename, "w") as title_file:
        title_file.write(document_source_path.name)
