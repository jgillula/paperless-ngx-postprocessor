#!/usr/bin/env python3

import argparse
import logging
import sys
import yaml

from paperlessngx_postprocessor import Config, PaperlessAPI, Postprocessor

if __name__ == "__main__":
    logging.basicConfig(format="[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s")#, level=logging.DEBUG)

    config = Config()
    
    arg_parser = argparse.ArgumentParser(description="Apply postprocessing to documents in Paperless-ngx",
                                         #formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                         epilog="See https://github.com/jgillula/paperless-ngx-postprocessor#readme for more information and detailed examples.")
    for option_name in config.options_spec.keys():
        arg_parser.add_argument("--" + option_name.replace("_","-"), **config.options_spec[option_name].argparse_args)
    
    selector_options = ["document_id", "correspondent", "document_type", "tag", "storage_path", "all", "restore"]
    arg_parser.add_argument("selector", metavar="SELECTOR", type=str, choices=selector_options, help="Selector to specify which document(s) to postprocess (or that you want to restore from a backup file). Choose one of {{{}}}".format(", ".join(selector_options)))
    arg_parser.add_argument("item_id_or_name", nargs='?', type=str, help="document_id or name of the correspondent/document_type/tag/storage_path of the documents to postprocess, or filename of the backup file to restore. Required for all selectors except 'all'.")

    cli_options = vars(arg_parser.parse_args())

    config.update_options(cli_options)

    config["selector"] = cli_options["selector"]
    config["item_id_or_name"] = cli_options["item_id_or_name"]

    logging.getLogger().setLevel(config["verbose"])
    logging.debug(f"Running {sys.argv[0]} with config {config}")
    
    if config["selector"] != "all" and config["item_id_or_name"] is None:
        if config["selector"] == "restore":
            logging.error(f"A filename is required to backup from.")
        else:
            logging.error(f"An item ID or name is required when postprocessing documents by {config['selector']}, but none was provided.")

    if config["selector"] == "restore" and config["backup"] is not None:
        logging.critical("Can't restore and do a backup simultaneously. Please choose one or the other.")
        sys.exit(1)

    if config["dry_run"]:
        logging.info("Doing a dry run. No changes will be made.")

    api = PaperlessAPI(config["paperless_api_url"],
                       auth_token = config["auth_token"],
                       paperless_src_dir = config["paperless_src_dir"],
                       logger=logging.getLogger())
    postprocessor = Postprocessor(api,
                                  config["rules_dir"],                                  
                                  postprocessing_tag = config["postprocessing_tag"],
                                  dry_run = config["dry_run"],
                                  logger=logging.getLogger())
    
    documents = []
    if config["selector"] == "restore":
        logging.info(f"Restoring backup from {config['item_id_or_name']}")
        with open(config["item_id_or_name"], "r") as backup_file:
            yaml_documents = list(yaml.safe_load_all(backup_file))
            logging.info(f" Restoring {len(yaml_documents)} documents")
            for yaml_document in yaml_documents:
                document_id = yaml_document['id']
                yaml_document.pop("id")
                current_document = api.get_document_by_id(document_id)
                logging.info(f"Restoring document {document_id}")
                for key in yaml_document:
                    logging.info(f" {key}: '{current_document.get(key)}' --> '{yaml_document[key]}'")
                if not config["dry_run"]:
                    api.patch_document(document_id, yaml_document)
        sys.exit(0)
    elif config["selector"] == "all":
        documents = api.get_all_documents()
        logging.info(f"Postprocessing all {len(documents)} documents")
    elif config["selector"] == "document_id":
        documents.append(api.get_document_by_id(config["item_id_or_name"]))
    elif config["selector"] in ["correspondent", "document_type", "tag", "storage_path"]:
        documents = api.get_documents_by_selector_name(config["selector"], config["item_id_or_name"])
        if len(documents) == 0:
            logging.warning(f"No documents found with {config['selector']} \'{config['item_id_or_name']}\'")
        else:
            logging.info(f"Postprocessing {len(documents)} documents with {config['selector']} \'{config['item_id_or_name']}\'")
    
    backup_documents = postprocessor.postprocess(documents)

    if len(backup_documents) > 0 and config["backup"] is not None:
        logging.debug(f"Writing backup to {config['backup']}")
        with open(config["backup"], "w") as backup_file:
            backup_file.write(yaml.dump_all(backup_documents))
