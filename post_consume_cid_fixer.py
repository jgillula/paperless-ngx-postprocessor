#!/usr/bin/env python3

import logging
import ocrmypdf
import os
from pathlib import Path
import regex
import shutil
import tempfile
from paperlessngx_postprocessor import Config, PaperlessAPI

if __name__ == "__main__":
    document_id = os.environ["DOCUMENT_ID"]

    config = Config()
    logging.basicConfig(format="[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s", level=config["verbose"])

    api = PaperlessAPI(config["paperless_api_url"],
                       auth_token = config["auth_token"],
                       paperless_src_dir = config["paperless_src_dir"])

    doc = api.get_document_by_id(document_id)
    if regex.fullmatch("(?m)^(?:\(cid:\d+\)\s*)+$", doc["content"]) is not None:
        logging.info(f"document_id {document_id} appears to consist entire of (cid:1234), fixing...")
        with tempfile.TemporaryDirectory(prefix="cid-fixer-") as temp_dir_name:
            temp_dir_path = Path(temp_dir_name)
            original_filename = temp_dir_path.joinpath("original.pdf")
            ocred_filename = temp_dir_path.joinpath("ocred.pdf")
            shutil.copy(os.environ["DOCUMENT_SOURCE_PATH"],
                        original_filename)
            ocrmypdf_args = {"input_file": original_filename,
                             "output_file": ocred_filename,
                             "progress_bar": False,
                             "use_threads": True,
                             "output_type": "pdf",
                             "force_ocr": True}
            ocrmypdf.ocr(**ocrmypdf_args)
            filename_to_consume = tempfile.mktemp(dir="/usr/src/paperless/consume",
                                                  suffix=".pdf")
            shutil.copy(ocred_filename, filename_to_consume)
            api.delete_document_by_id(document_id)
            
        logging.info(f"  ...done")
    else:
        logging.debug(f"document_id {document_id} appeared to be OCRed successfully, so not trying again")
