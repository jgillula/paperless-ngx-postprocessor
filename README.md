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

paperless-ngx-postprocessor works by reading rules from the `rules.d` folder, seeing if the contents of the document match any of the rules, extracting values from the document's contents using a regular expression, and then writing new values for the metadata based on the document's preexisting metadata and any values extracted using the regular expression.

### An example

An example helps illustrate this. Say you have the following rules:
```yaml
Some Rule Name:
  match: "{{ correspondent == 'The Bank' and document_type == 'Transfer Confirmation' }}"
  metadata_regex: '(?:From (?P<source>.*?)\n)|(?:through (?P<created_month>\w*?) (?P<created_day>\d{1,2}), (?P<created_year>\d{4}))'
  metadata_postprocessing:
    source: '{{ source | title }}' # This applies the Jinja 'title' filter, capitalizing each word
    title: '{{created_year}}-{{created_month}}-{{created_day}} -- {{correspondent}} -- {{document_type}} (from {{ source }})'
```

First paperless-ngx-postprocessor will get a local copy of the document's preexisting metadata. For a full list of the preexisting metadata you can use for matching and postprocessing, see FIXME.

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
* `created_month` will be turned into a zero-padded two-digit string (e.g. '04'). If `created_month` is a string and appears to be the name or abbreviation of a month in the current locale (ignoring capitalization) it will be converted to its corresponding number (e.g. 'Apr' or 'april' will be converted to '04').
* `created_year` has no normalization. If you want to convert a two-digit year to a four-digit year, you can use the special Jinja filter `expand_two_digit_year`, like so: `{{ created_year | expand_two_digit_year }}`. By default this will add the current century, e.g. as of 2022 this will turn `63` into `2063`. If you want to set a different century, just pass it to the filter like so: `{{ created_year | expand_two_digit_year(19) }}` (converting `77` to `1977`).

For all three, if the new value is ever not convertible into an `int`, then it's rejected and the old value is used (either the original `created_day`, or the last good value before the current individual postprocessing rule).
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
