# paperless-ngx-postprocessor
A powerful and customizable postprocessing script for [paperless-ngx](https://github.com/paperless-ngx/paperless-ngx#readme).

paperless-ngx-postprocessor allows you to automatically set titles, ASNs, and created dates based on data extracted from the contents of your documents. The recommended use is to run it as a [post-consumption script](https://paperless-ngx.readthedocs.io/en/latest/advanced_usage.html#post-consumption-script) with Paperless-ngx, so that it automatically sets the metadata whenever Paperless-ngx consumes a new document. It also has a management mode, which allows you to run it standalone.

## Features

* Setup rulesets to choose which documents are postprocessed and which are ignored, based on metadata like correspondent, document_type, storage_path, tags, and more
* For each ruleset, extract metadata using [Python regular expressions](https://docs.python.org/3/library/re.html#regular-expression-syntax)
* Use [Jinja templates](https://jinja.palletsprojects.com/en/3.1.x/templates/) to specify new values for archive serial number, title, and created date, using the values from your regular expression
* Optionally apply a tag to documents that are changed during postprocessing, so you can keep track of which documents have changed
* Optionally make backups of changes, so you can restore document metadata back to the way it was before postprocessing
* Optionally run on one or more existing documents, if you need to adjust the metadata of documents that have already been consumed by Paperless-ngx
* Optionally call *another script* as a post-consumption script after running paperless-ngx-postprocessor, so you don't have to give up your existing post-consumption script

## Getting Started

The following instructions assume your Paperless-ngx instance is running using docker-compose. If you're running some other way, the following instructions should give you a general idea of what to do. If you still can't figure it out, [file an issue](https://github.com/jgillula/paperless-ngx-postprocessor/issues/new) and I'll write up some documentation. (I just didn't want to write documentation nobody was going to use.)

### 0. Get the code

First, clone this paperless-ngx-postprocessor repository to the same host machine where your Paperless-ngx docker container is running.
```bash
git clone https://github.com/jgillula/paperless-ngx-postprocessor.git
```

### 1. Setup paperless-ngx

Next we'll need to edit Paperless-ngx's `docker-compose.yml` and `docker-compose.env` files to find paperless-ngx-postprocessor. (You'll find these in whichever directory you used to setup your paperless-ngx docker instance.) In `docker-compose.yml`, find the list of `volumes` under the `webserver` entry, and add the following line (appropriately indented):
```yaml
- /whichever/directory/you/cloned/paperless-ngx-postprocessor/into:/usr/src/paperless-ngx-postprocessor
```
e.g. I might have
```yaml
- /home/jgillula/paperless-ngx-postprocessor:/usr/src/paperless-ngx-postprocessor
```

Next open `docker-compose.env` and add the following line:
```bash
PAPERLESS_POST_CONSUME_SCRIPT=/usr/src/paperless-ngx-postprocessor/post_consume_script.sh
```

Now recreate and start paperless-ngx by running
```bash
docker-compose up -d
```

### 2. Run the one-time setup script inside the Paperless-ngx docker container

Still in the directory of your Paperless-ngx instance, run the following command to setup a Python virtual environment inside the docker container:
```bash
docker-compose exec -u paperless webserver /usr/src/paperless-ngx-postprocessor/setup_venv.sh
```

### 3. Create an auth token
Next we'll need create an authentication token in your Paperless-ngx instance. To do this, go to the 'Add token' page in your paperless-ngx admin console, e.g. [http://localhost:8000/admin/authtoken/tokenproxy/add/](http://localhost:8000/admin/authtoken/tokenproxy/add/). Choose which user you want paperless-ngx-postprocessor to run as, and then click "SAVE".

### 4. Create rulesets to postprocess your documents

Last but not least, create rulesets in the `paperless-postprocessor-ngx/rulesets.d` folder to start postprocessing your documents. See below on how to write rulesets.

## How it works

paperless-ngx-postprocessor works by reading rulesets from all the `.yml` files in the `rulesets.d` folder, seeing if the contents of the document match any of the rulesets, extracting values from the document's contents using a regular expression, and then writing new values for the metadata based on the document's preexisting metadata and any values extracted using the regular expression.

### An example

An example helps illustrate this. Say you have the following ruleset:
```yaml
Some Ruleset Name:
  match: "{{ correspondent == 'The Bank' and document_type == 'Transfer Confirmation' }}"
  metadata_regex: '(?:From (?P<source>.*?)\n)|(?:through (?P<created_month>\w*?) (?P<created_day>\d{1,2}), (?P<created_year>\d{4}))'
  metadata_postprocessing:
    source: '{{ source | title }}' # This applies the Jinja 'title' filter, capitalizing each word
    title: '{{created_year}}-{{created_month}}-{{created_day}} -- {{correspondent}} -- {{document_type}} (from {{ source }})'
```

First paperless-ngx-postprocessor will get a local copy of the document's preexisting metadata. For a full list of the preexisting metadata you can use for matching and postprocessing, see [below](#available-metadata).

Next, paperless-ngx-postprocessor will try to see if the document matches by evaluating the Jinja template given in the `match` field, filling in values from our local copy of the document's metadata. In this case, the document's `correspondent` must be `The Bank` and  its `document_type` must be `Transfer Confirmation`. If that's true, the Jinja template will evaluate to `True`, and the document is a match for further postprocessing.

Next, values are extracted from the document using the Python regular expression given in the `metadata_regex` field, through the use of [named groups](https://docs.python.org/3/library/re.html#regular-expression-syntax:~:text=in%20a%20group.-,(%3FP%3Cname%3E...),-Similar%20to%20regular). In this case there are four named groups that will be extracted (if they're found in the document's contents): `source`, `created_month`, `created_day`, and `created_year`. All of these values are added to our local copy of the document's metadata, overwriting existing values if they exist. In this case `source` is a new field that's created; all of the others replace the existing values that were already in our local copy.

Next, the metadata is postprocessed using the individual postprocessing rules listed in the `metadata_postprocessing` field. Each step specifies which piece of metadata to edit, and the Jinja template tells us how to edit it. paperless-ngx-postprocessor will evaluate the given Jinja template using our local copy of the document's metadata as it exists given all the replacing and editing we've done so far.

For example, the `source` rule tells us to take the `source` field and apply the Jinja `title` filter to it, which just capitalizes each word. We then store the newly capitalized value of `source` for use in further fields. And lo and behold, in the next field, `title`, we make use of it! In `title` we tell paperless-postprocess-ngx to set the `title` field to something that looks like `2022-09-21 -- The Bank -- Transfer Confirmation (from The Other Bank)`.

Finally after all the rules are processed, paperless-ngx-postprocessor will take the final values of five special fields:
* `asn`
* `title`
* `created_year`, `created_month`, and `created_day`

If any of those differ from the values the document's metadata had when we started, then paperless-ngx-postprocessor will push the new values to paperless-ngx, and processing is complete.

### Some caveats

In order to make parsing dates easier, paperless-postprocessor-ngx will "normalize" and error-check the `created_year`, `created_month`, and `created_day` fields after the initial values are extracted using the regular expression, and after every individual postprocessing rule.

Normalization is as follows:
* `created_day` will be turned into a zero-padded two-digit string (e.g. `09`).
* `created_month` will be turned into a zero-padded two-digit string (e.g. `04`). If `created_month` is a string and appears to be the name or abbreviation of a month in the current locale (ignoring capitalization) it will be converted to its corresponding number (e.g. `Apr` or `april` will be converted to `04`).
* `created_year` has no normalization. If you want to convert a two-digit year to a four-digit year, you can use the special Jinja filter `expand_two_digit_year`, like so: `{{ created_year | expand_two_digit_year }}`. By default this will add the current century, e.g. as of 2022 this will turn `63` into `2063`. If you want to set a different century, just pass it to the filter like so: `{{ created_year | expand_two_digit_year(19) }}` (converting `77` to `1977`).

For all three, if the new value is ever not convertible into an `int`, then it's rejected and the old value is used (either the original value from the document's metadata before any postprocessing, or the last good value before the current individual postprocessing rule).

This normalization and error-checking allows you to extract dates from the document's contents without having to worry about their format or converting month names to numbers. Instead, paperless-ngx-postprocessor does all that for you.

### Custom Jinja filters

In addition to the [default Jinja filters](https://jinja.palletsprojects.com/en/3.1.x/templates/#builtin-filters) the following custom filters are available:

* `expand_two_digit_year(prefix=None)`
  * Convert a two-digit year to a four-digit year. By default this will add the current century, e.g. as of 2022 this will turn `63` into `2063`. If you want to set a different century, just pass it to the filter like so: `{{ created_year | expand_two_digit_year(19) }}` (converting `77` to `1977`).
* `regex_match(pattern)`
  * Matches using `re.match()`. Only returns `True` or `False`. For details see the [official python documentation](https://docs.python.org/3/library/re.html#re.match).
* `regex_sub(pattern, repl)`
  * Substitutes using `re.sub()`. For details see the [official python documentation](https://docs.python.org/3/library/re.html#re.sub).

These can be used like this:
```
{{ variable | custom_filter("parameter") }}
```
See [rulesets.d/example.yml](rulesets.d/example.yml) for examples of how to use these filters.

### Combining rulesets

paperless-ngx-postprocessor reads all of the files in the `rulesets.d` folder in order, alphabetically by name. In each file, all of the postprocessing rulesets in the given file are also read in order.

Each ruleset that matches a given document is applied one at a time, and the changes from an earlier ruleset will affect what metadata is available in a later ruleset. Additionally, the individual field rules are applied in order, and the changes in one affect what metadata is available in a later rule in the same ruleset. For a given document, metadata created in an earlier ruleset persists across later rulesets (unless changed).

For example, say you had the following rulesets:
```yaml
First Ruleset:
  match: True
  metadata_regex: 'foo is here (?P<foo>\w+)'
  metadata_postprocessing:
    bar: '{{ foo | upper }'
    foo: "{{ 'it is uppercase' if (foo | upper) == bar else 'it is not uppercase' }"
    title: '{{ foo }}'
---
Second Ruleset:
  match: True
  metadata_regex: 'foo is here (?P<foo>\w+)'
  metadata_postprocessing:
    foo: "{{ foo | lower }}"
    title: "{{ foo }} {{ title }}"
---
Third Ruleset
    match: True
    metadata_regex: 'foo is here (?P<foo>\w+)'
    metadata_postprocessing:
      title: "uppercase foo is {{ bar }}"
```

And let's say the contents of the document was a single line:
```
foo is here You_found_Me
```

Each of the rules will match any and every document (since their `match` field is `True`), so postprocessing would proceed as follows:
1. In the `First Ruleset`, we would first extract `foo` with the value `You_found_Me`. 
   1. We would then set `bar` to `YOU_FOUND_ME`.
   2. Then since `bar` is equal to `foo` in all caps, we would set `foo` to `it is uppercase`.
   3. Finally, we would set `title` to `{{ foo }}`, which has the value `it is uppercase`.
1. Then in the `Second Ruleset`, we would extract `foo` as before.
   2. We would then set `foo` to `you_found_me`
   3. We would then set the `title` to `you_found_me it is uppercase`, since the `title` had been updated by the previous ruleset.
5. Finally in `Third Ruleset`, we would extract `foo` as before:
   6. Since fields persist across rulesets, and `bar` was set in the `First Ruleset`, title will be set to `uppercase foo is YOU_FOUND_ME`.
   7. This title will then be used to finally update paperless-ngx.

## Formal ruleset definition

### Ruleset syntax

Each ruleset is a single YAML document defined as follows:
```yaml
Ruleset Name:
  match: MATCH_TEMPLATE
  metadata_regex: REGEX
  metadata_postprocessing:
    METADATA_FIELDNAME_1: METADATA_TEMPLATE_1
    ...
    METADATA_FIELDNAME_N: METADATA_TEMPLATE_N
```
where
* `MATCH_TEMPLATE` is a Jinja template. If it evaluates to True, the ruleset will match and postprocessing will continue.
* `metadata_regex` is optional. If specified,`REGEX` is a Python regular expression. Any named groups in `REGEX` will be saved and their values can be used in the postprocessing rules in this ruleset.
* `metadata_postprocessing` is optional. If not specified, then paperless-ngx-postprocessor will update the document's metadata based only on the fields extract from the regular expression.
* `METADATA_FIELDNAME_X` is the name of a metadata field to update, and `METADATA_TEMPLATE_X` is a Jinja template that will be evaluated using the metadata so far. You can have as many metadata fields as you like.

### Available metadata:

The metadata available for matching and postprocessing mostly matches [the metadata available in paperless-ngx for filename handling](https://paperless-ngx.readthedocs.io/en/latest/advanced_usage.html#file-name-handling).

The following fields are read-only. They keep the same value through postprocessing as they had before postprocessing started. (If you try to overwrite them with new values, those values will be ignored.)
* `correspondent`: The name of the correspondent, or `None`.
* `document_type`: The name of the document type, or `None`.
* `tag_list`: A list object containing the names of all tags assigned to the document.
* `storage_path`: The name of the storage path, or `None`.
* `added`: The full date (ISO format) the document was added to paperless.
* `added_year`: Year added only (as a `str`, not an `int`).
* `added_month`: Month added only, number 01-12 (as a `str`, not an `int`).
* `added_day`: Day added only, number 01-31 (as a `str`, not an `int`).

The following fields are available for matching, and can be overwritten by values extracted from the regular expression (e.g. by using a named group with the field name) or by postprocessing rules.
* `asn`: The archive serial number of the document, or `None`.
* `title`: The title of the document.
* `created_year`: Year created only (as a `str`, not an `int`).
* `created_month`: Month created only, number 01-12 (as a `str`, not an `int`).
* `created_day`: Day created only, number 01-31 (as a `str`, not an `int`).

The following fields are read-only, but will be updated automatically after every step by the values given in the `created_year`, `created_month`, and `created_day` fields.
* `created`:  The full date (ISO format) the document was created.
* `created_date`: The date the document was created in `YYYY-MM-DD` format.

## Configuration

paperless-ngx-postprocessor can be configured using the following environment variables. The defaults should work for a typical paperless-ngx deployment done via docker-compose. If you want to change them, just add them to the same `docker-compose.env` file as you use for Paperless-ngx, and they will be passed along from Paperless-ngx to paperless-ngx-postprocessor.

* `PNGX_POSTPROCESSOR_AUTH_TOKEN=<token>`: The auth token to access the REST API of Paperless-ngx. If not specified, postprocessor will try to automagically get it from Paperless-ngx's database directly. (default: `None`)
* `PNGX_POSTPROCESSOR_DRY_RUN=<bool>`: If set to `True`, paperless-ngx-postprocessor will not actually push any changes to paperless-ngx. (default: `False`)
* `PNGX_POSTPROCESSOR_BACKUP=<bool or path>`: Backup file to write any changed values to. If no filename is given, one will be automatically generated based on the current date and time. If the path is a directory, the automatically generated file will be stored in that directory. (default: `False`)
* `PNGX_POSTPROCESSOR_POSTPROCESSING_TAG=<tag name>`: A tag to apply if any changes are made during postprocessing. (default: `None`)
* `PNGX_POSTPROCESSOR_RULESETS_DIR=<directory>`: The config directory (within the Docker container) containing the rulesets for postprocessing. (default: `/usr/src/paperless-ngx-postprocessor/rulesets.d`)
* `PNGX_POSTPROCESSOR_PAPERLESS_API_URL=<url>`: The full URL to access the Paperless-ngx REST API (within the Docker container). (default: `http://localhost:8000/api`)
* `PNGX_POSTPROCESSOR_PAPERLESS_SRC_DIR=<directory>`: The directory containing the source for the running instance of paperless-ngx (within the Docker container). If this is set incorrectly, postprocessor will not be able to automagically acquire the auth token. (default: `/usr/src/paperless/src`)
* `PNGX_POSTPROCESSOR_POST_CONSUME_SCRIPT=<full path to script>`: A post-consumption script to run *after* paperless-ngx-postprocessor is done. All of the environment variables and parameters will be as described in [paperless-ngx's documentation](https://paperless-ngx.readthedocs.io/en/latest/advanced_usage.html#hooking-into-the-consumption-process) (except the values will reflect any new values updated during postprocessing).

## Management

In addition to being run as a post-consumption script, paperless-ngx-postprocessor has the ability to be run directly via a command line interface using the `paperlessngx_postprocessor.py` script. The primary use case is if you've changed some of your postprocessing rules and want to apply the new postprocessing rules to some of your documents without deleting them from Paperless-ngx and re-importing them.

There are two ways to run `paperlessngx_postprocessor.py` as a management script: inside the docker container and outside. In both cases, you have to make sure that you've activated an appropriate Python virtual environment so that `paperlessngx_postprocessor.py` can find the Python modules it depends on to run.

### Running the management script inside the Paperless-ngx docker container

In order to run `paperlessngx_postprocessor.py` inside the Paperless-ngx docker container, you can enter the following line *on the Docker host*, in the directory that contains `docker-compose.yml` for Paperless-ngx (e.g. `/var/local/paperless-ngx`), in order to get a bash terminal inside the Paperless-ngx docker container:
```bash
docker-compose exec -u paperless webserver /bin/bash
```
This should bring you into the docker container, and then you can navigate to the appropriate directory inside the docker container, activate the Python virtual environment, and run `paperlessngx_postprocessor.py`:
```bash
cd /usr/src/paperless-ngx-postprocessor
source venv/bin/activate
./paperlessngx_postprocessor.py --help
```

### Running the management script from the docker host

In order to run `paperlessngx_postprocessor.py` outside the Paperless-ngx docker container, you'll probably need to set up a new Python virtual environment, instead of using the one inside the Docker container, e.g. do the following on the docker *host*:
```bash
mkdir ~/some/directory/to/keep/the/virtual/environment
cd ~/some/directory/to/keep/the/virtual/environment
python -m venv --system-site-packages venv
source venv/bin/activate
pip install -r /whichever/directory/you/cloned/paperless-ngx-postprocessor/into/requirements.txt
```

Then any time you want to run `paperlessngx_postprocessor.py` you need to make sure to activate the Python virtual environment first (you only need to do so once, until you close that terminal), e.g. on the docker host:
```bash
cd ~/some/directory/to/keep/the/virtual/environment
source venv/bin/activate
/whichever/directory/you/cloned/paperless-ngx-postprocessor/into/paperlessngx_postprocessor.py --help
```

Note that to run the management script from the docker host, you need to provide the auth token you generated during setup, e.g. (on the docker host):
```bash
./paperlessngx_postprocessor.py --auth-token THE_AUTH_TOKEN [specific command here]
```

### Running inside or outside the docker container

Note that no matter where you run it, `paperlessngx_postprocessor.py` will try to use sensible defaults to figure out how to access the Paperless-ngx API. If you have a custom configuration, you may need to specify additional configuration options to `paperlessngx_postprocessor.py`. See [Configuration](#configuration) above for more details.

In terms of how the script works in management mode, it runs post-processing on all documents given a particular criteria. In other words, you provide some criteria for what documents to re-run postprocessing on, and then `paperlessngx_postprocessor.py` will process each of those documents as if seeing it for the very first time, applying postprocessing.

For example to re-run postprocessing on all documents with `correspondent` `The Bank`, you would do the following (including the auth token if running this command from the Docker host):
```bash
./paperlessngx_postprocessor.py [--auth-token THE_AUTH_TOKEN] correspondent "The Bank"
```

You can choose all documents of a particular `correspondent` or `document_type` or `storage_path`, all documents with a specific `tag`, or just all documents (using `all`), or a specific document using its `document_id`. Note that you cannot combine selectors on the command line: e.g it's not possible to select all documents that match both a given `document_type` and `tag` simultaneously on the command line.

The command line interface supports all of the same options that you can set via the environment variables listed in the [Configuration section above](#configuration). To see how to specify them, use the command line interface's built-in help:
```bash
./paperlessngx_postprocessor.py --help
```

### Dry-runs, backups, and restores

The command line interface also supports two feature that you can't do as a post-consumption script.

First, you can do a dry-run to see what *would* change as a result of postprocessing, without actually applying the changes:
```bash
./paperlessngx_postprocessor.py --dry-run [the rest of the specific command here]
```
This is helpful when you are trying to get your postprocessing rules right, since you can see what the effect would be without messing up your documents.


You can also make a backup when you apply postprocessing:
```bash
./paperlessngx_postprocessor.py --backup [the rest of the specific command here]
```
This will write a backup file with any fields that were changed by `paperlessngx_postprocessor.py` as they were *before* the changes were made.

To restore backup to undo changes, do:
```bash
./paperlessngx_postprocessor.py restore path/to/the/backup/file/to/restore
```

If you want to see what the restore will do, you can open up the backup file in a text editor. Inside is just a yaml document with all of the document IDs and what their fields should be restored to.

## FAQ

### Will this work with paperless or paperless-ng?

Nope, just paperless-ngx.
