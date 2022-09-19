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
