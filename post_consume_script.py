#!/usr/bin/env python3

import logging
import os
import subprocess
import sys
from pathlib import Path

from paperlessngx_postprocessor import Config, PaperlessAPI, Postprocessor

if __name__ == "__main__":
    directory = os.path.abspath(os.path.dirname(__file__))

    document_id = os.environ.get("DOCUMENT_ID")

    if document_id is not None:
        subprocess.run((str(Path(directory)/"paperlessngx_postprocessor.py"),
                        "document_id",
                        document_id))

        post_consume_script = os.environ.get("PNGX_POSTPROCESSOR_POST_CONSUME_SCRIPT")
        if post_consume_script is not None:
            logging.basicConfig(format="[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s")
            
            config = Config()
            
            logging.getLogger().setLevel(config["verbose"])
            
            script_env = os.environ.copy()
            
            api = PaperlessAPI(config["paperless_api_url"],
                               auth_token = config["auth_token"],
                               paperless_src_dir = config["paperless_src_dir"],
                               logger=logging.getLogger())    
            
            script_env.update(api.get_metadata_for_post_consume_script(document_id))
            for key in script_env:
                if script_env[key] is None:
                    script_env[key] = "None"

            logging.debug(f"Running post consume script {post_consume_script} with environment f{script_env}")

            subprocess.run((post_consume_script,
                            script_env["DOCUMENT_ID"],
                            script_env["DOCUMENT_FILE_NAME"],
                            script_env["DOCUMENT_SOURCE_PATH"],
                            script_env["DOCUMENT_THUMBNAIL_PATH"],
                            script_env["DOCUMENT_DOWNLOAD_URL"],
                            script_env["DOCUMENT_THUMBNAIL_URL"],
                            script_env["DOCUMENT_CORRESPONDENT"],
                            script_env["DOCUMENT_TAGS"]),
                           env=script_env)
        

