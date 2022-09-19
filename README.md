# paperless-ngx-postprocessor
A powerful and customizable postprocessing script for [paperless-ngx](https://github.com/paperless-ngx/paperless-ngx#readme).

paperless-ngx-postprocessor allows you to automatically set titles, ASNs, and created dates based on data extracted from the contents of your documents. The recommended use is to run it as a [post-consumption script](https://paperless-ngx.readthedocs.io/en/latest/advanced_usage.html#post-consumption-script) with Paperless-ngx, so that it automatically sets the metadata whenever Paperless-ngx consumes a new document. It also has a management mode, which allows you to run it standalone.

## Features

* Setup rules to match how documents are postprocessed, based on metadata like correspondent, document_type, storage_path, tags, and more
* For each rule, extract metadata using [Python regular expressions](https://docs.python.org/3/library/re.html#regular-expression-syntax)
* Use [Jinja templates](https://jinja.palletsprojects.com/en/3.1.x/templates/) to specify new values for archive serial number, title, and created date, using the values from your regular expression
* Optionally apply a tag to documents that are changed during postprocessing, so you can keep track of which documents have changed
* Optionally make backups of changes, so you can restore document metadata back to the way it was before postprocessing
* Optionally run on one or more existing documents, if you need to adjust the metadata of documents that have already been consumed by Paperless-ngx
* Optionally call *another script* as a post-consumption script after running paperless-ngx-postprocessor, so you don't have to give up your existing post-consumption script

## Getting Started

The following instructions assume your Paperless-ngx instance is running using docker-compose. If you're running some other way, the following instructions should give you a general idea of what to do. If you still can't figure it out. File an issue and I'll write up some documentation. (I just didn't want to write documentation nobody was going to use.)

### 0. Get the code

First, clone the paperless-ngx-postprocessor repository wherever you would like the code to live:
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
docker-compose exec -u paperless webserver /usr/src/paperless-ngx-postprocessor/setup_env.sh
```

### 3. Create an auth token
Next we'll need create an authentication token in your Paperless-ngx instance. To do this, go to the 'Add token' page in your paperless-ngx admin console, e.g. [http://localhost:8000/admin/authtoken/tokenproxy/add/](http://localhost:8000/admin/authtoken/tokenproxy/add/). Choose which user you want paperless-ngx-postprocessor to run as, and then click "SAVE".

### 4. Create rules to postprocess your documents

Last but not least, create rules in the `paperless-postprocessor-ngx/rules.d` folder to start postprocessing your documents.

## How it works

paperless-ngx-postprocessor runs using the following algorithm:
1. Read all of the files in the `rules.d` folder in order, alphabetically by name. In each file, read all of the postprocessing rules in the given file, in order.
1. To postprocess a document, cycle through each of the rules in order. If the document matches the current rule, do the following.
   1. Get a copy of the document's metadata (let's call it `postprocessing_metadata`)
   1. Extract values from the document's contents using the `metadata_regex` field, and add it to `postprocessing_metadata`, overwriting existing values
   1. Cycle through each of the `metadata_postprocessing` fields in order. For each field:
      1. Evaluate the Jinja template using `postprocessing_metadata`
      1. Set the new value for the given field in `postprocessing_metadata` to whatever the template evaluated to
1. After all the rules have been applied, get the `title`, `asn`, and `created_date` from the last version of `postprocessing_metadata`, and if they're different from the document's current values, update them in Paperless-ngx

Additionally, note that at every stage the `created_day` field is automatically converted to a zero-padded day (e.g. `07`), and `created_month` is converted to a zero-padded month (e.g. `09). If `created_month` is a string that matches the name of a month (e.g. `sep` or `September`), then it is automatically converted to the corresponding number.

An example helps illustrate this. Say you have the following rules:
```yaml
Some Rule Name:
  match: "{{ correspondent == 'The Bank' and document_type == 'Transfer Confirmation' }}"
  metadata_regex: '(?:From (?P<source>.*?)\n)|(?:through (?P<created_month>\w*?) (?P<created_day>\d{1,2}), (?P<created_year>\d{2}))'
  metadata_postprocessing:
    created_year: "{{ created_year | expand_year }}" # This uses the 'expand_year' filter, which will take a two-digit year like 57 and turn it into a four-digit year like 2057
    source: '{{ source | title }}' # This applies the Jinja2 'title' filter, capitalizing each word
    title: '{{created_year}}-{{created_month}}-{{created_day}} -- {{correspondent}} -- {{document_type}} (from {{ source }})'
---
# You can put multiple rules in the same file if you want
# Note that rules are applied in order, so any changes from this rule will overwrite changes from previous rules
Some Other Rule Name:
  # This will always match
  match: True
  metadata_postprocessing:
    title: '{{created_year}}-{{created_month}}-{{created_day}} -- {{correspondent}} -- {{document_type}}'
```

First, paperless-ngx-postprocessor will see if the document's correspondent is `The Bank` and if its document_type is `Transfer Confirmation`. If so, it will extract four values from the document's contents by applying the first regular expression (as given by the four [named groups](https://docs.python.org/3/library/re.html#regular-expression-syntax:~:text=in%20a%20group.-,(%3FP%3Cname%3E...),-Similar%20to%20regular): `source`, `created_month`, `created_day`, and `created_year`.
