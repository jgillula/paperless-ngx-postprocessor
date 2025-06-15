#!/usr/bin/env python3

import argparse
import logging
import sys
import yaml
import os
import copy

from paperlessngx_postprocessor import Config, PaperlessAPI, Postprocessor

if __name__ == "__main__":
    logging.basicConfig(format="[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s")#, level=logging.DEBUG)

    config = Config(Config.general_options())
    
    arg_parser = argparse.ArgumentParser(description="Apply postprocessing to documents in Paperless-ngx",
                                         #formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                         epilog="See https://github.com/jgillula/paperless-ngx-postprocessor#readme for more information and detailed examples.")
    for option_name in config.options_spec.keys():
        arg_parser.add_argument("--" + option_name.replace("_","-"), **config.options_spec[option_name].argparse_args)

        #    arg_parser.add_argument("--select", metavar=("ADDITIONAL_SELECTOR", "ITEM_NAME"), nargs=2, action="append", help="Additional optional selectors to apply to narrow the set of documents to apply postprocessing to. Ignored if SELECTOR is one of {all, document_id, restore}. ADDITIONAL_SELECTOR must be one of {correspondent, document_type, tag, storage_path}.")

    subparsers = arg_parser.add_subparsers(dest="mode", title='Modes', help="Use 'process [ARGS]' to choose which documents to process, or 'restore FILENAME' to restore a backup file.")

    process_subparser = subparsers.add_parser("process", usage=f"{os.path.basename(__file__)} [OPTIONS] process [SELECTORS]", description='Process documents where all the [SELECTORS] match (e.g. a collective "and"). At least one selector is required. If --all or --document-id is given, all the other selectors are ignored. For help with general [OPTIONS], do \'paperlessngx_postprocessor.py --help\'')
    selector_group = process_subparser.add_argument_group(title="SELECTORS")
    selector_config = Config(Config.selector_options(), use_environment_variables=False)
    for option_name in selector_config.options_spec.keys():
        selector_group.add_argument("--" + option_name.replace("_","-"), **selector_config.options_spec[option_name].argparse_args)

    restore_subparser = subparsers.add_parser("restore", usage=f"{os.path.basename(__file__)} [OPTIONS] restore FILENAME")
    restore_subparser.add_argument("filename", metavar="FILENAME", type=str, help="Filename of the backup file to restore.")

    cli_options = vars(arg_parser.parse_args())

    config.update_options(cli_options)
    selector_config.update_options(cli_options)

    # config["selector"] = cli_options["selector"]
    # config["item_id_or_name"] = cli_options["item_id_or_name"]

    config["mode"] = cli_options["mode"]
    config["filename"] = cli_options.get("filename")

    logger = logging.getLogger("paperlessngx_postprocessor")
    logger.setLevel(config["verbose"])
    # If we're in debug mode, sanitize the config to not print auth tokens
    if logger.level <= logging.DEBUG:
        sanitized_config = copy.deepcopy(config)
        if sanitized_config['auth_token'] is not None:
            sanitized_config['auth_token'] = "XXXXXXXX"
        logger.debug(f"Running {sys.argv[0]} with config {sanitized_config} and {selector_config}")

    # if config["selector"] != "all" and config["item_id_or_name"] is None:
    #     if config["selector"] == "restore":
    #         logging.error(f"A filename is required to backup from.")
    #     else:
    #         logging.error(f"An item ID or name is required when postprocessing documents by {config['selector']}, but none was provided.")

    if config["mode"] == "restore" and config["backup"] is not None:
        logger.critical("Can't restore and do a backup simultaneously. Please choose one or the other.")
        sys.exit(1)

    if config["dry_run"]:
        # Force at least info level, by choosing whichever level is lower, the given level or info (since more verbose is lower)
        logger.setLevel(min(logging.getLevelName(config["verbose"]), logging.getLevelName("INFO")))
        logger.info("Doing a dry run. No changes will be made.")

    api = PaperlessAPI(config["paperless_api_url"],
                       auth_token = config["auth_token"],
                       paperless_src_dir = config["paperless_src_dir"],
                       logger=logger)
    postprocessor = Postprocessor(api,
                                  config["rulesets_dir"],                                  
                                  postprocessing_tag = config["postprocessing_tag"],
                                  invalid_tag = config["invalid_tag"],
                                  dry_run = config["dry_run"],
                                  skip_validation = config["skip_validation"],
                                  logger=logger)
    
    documents = []
    if config["mode"] == "restore":
        logger.info(f"Restoring backup from {config['filename']}")
        with open(config["filename"], "r") as backup_file:
            yaml_documents = list(yaml.safe_load_all(backup_file))
            logger.info(f" Restoring {len(yaml_documents)} documents")
            for yaml_document in yaml_documents:
                document_id = yaml_document['id']
                yaml_document.pop("id")
                current_document = api.get_document_by_id(document_id)
                logger.info(f"Restoring document {document_id}")
                for key in yaml_document:
                    logger.info(f" {key}: '{current_document.get(key)}' --> '{yaml_document[key]}'")
                if not config["dry_run"]:
                    api.patch_document(document_id, yaml_document)
        sys.exit(0)
    elif config["mode"] == "process":
        if selector_config["all"]:
            documents = api.get_all_documents()
            logger.info(f"Postprocessing all {len(documents)} documents")
        elif not(any(selector_config.values())):
            logger.error("No SELECTORS provided. Please specify at least one SELECTOR.")
            sys.exit(1)
        elif selector_config.get("document_id"):
            documents.append(api.get_document_by_id(selector_config.get("document_id")))
        else:
            documents = api.get_documents_by_field_names(**selector_config.options())

        # Filter out any null documents, and then warn if no documents are left
        documents = list(filter(lambda doc: doc, documents))
        if len(documents) == 0:
            logger.warning(f"No documents found")
            sys.exit(0)
        else:
            logger.info(f"Processing {len(documents)} documents.")
        #     documents.append(api.get_

        # elif config["selector"] == "all":
        #     documents = api.get_all_documents()
        #     logger.info(f"Postprocessing all {len(documents)} documents")
        # elif config["selector"] == "document_id":
        #     documents.append(api.get_document_by_id(config["item_id_or_name"]))
        # elif config["selector"] in ["correspondent", "document_type", "tag", "storage_path"]:
        #     fields = {config["selector"]: config["item_id_or_name"]}
        #     documents = api.get_documents_by_field_names()
        #     # documents = api.get_documents_by_selector_name(config["selector"], config["item_id_or_name"])
        #     # if len(documents) == 0:
        #     #     logger.warning(f"No documents found with {config['selector']} \'{config['item_id_or_name']}\'")
        #     # else:
        #     #     logger.info(f"Postprocessing {len(documents)} documents with {config['selector']} \'{config['item_id_or_name']}\'")

        backup_documents = postprocessor.postprocess(documents)

        if len(backup_documents) > 0 and config["backup"] is not None:
            logger.debug(f"Writing backup to {config['backup']}")
            with open(config["backup"], "w") as backup_file:
                backup_file.write(yaml.dump_all(backup_documents))
