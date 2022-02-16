[![PyPI](https://img.shields.io/pypi/v/contextualise.svg)](https://pypi.org/project/contextualise/)
[![Python 3.x](https://img.shields.io/pypi/pyversions/contextualise.svg?logo=python&logoColor=white)](https://pypi.org/project/contextualise/)
[![GitHub open issues](https://img.shields.io/github/issues/brettkromkamp/contextualise)](https://github.com/brettkromkamp/contextualise/issues?q=is%3Aopen+is%3Aissue)
[![GitHub closed issues](https://img.shields.io/github/issues-closed/brettkromkamp/contextualise)](https://github.com/brettkromkamp/contextualise/issues?q=is%3Aissue+is%3Aclosed)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/brettkromkamp/contextualise/blob/master/LICENSE)

# Contextualise: Structured Knowledge

Contextualise is an effective tool particularly suited for organising information-heavy projects and activities consisting of unstructured and widely diverse data and information resources &mdash; think of investigative journalism, personal and professional research projects, [world building](https://en.wikipedia.org/wiki/Worldbuilding) (for books, movies or computer games) and many kinds of hobbies.

Contextualise's main dependency is [TopicDB](https://github.com/brettkromkamp/topic-db), an open source [topic maps](https://msdn.microsoft.com/en-us/library/aa480048.aspx)-based graph store. Topic maps provide a way to describe complex relationships between abstract concepts and real-world (information) resources.

> Check out the [Awesome Knowledge Management](https://github.com/brettkromkamp/awesome-knowledge-management) resource, a curated list of amazingly awesome articles, people, projects, applications, software libraries and projects related to the knowledge management space. Alternatively, if you are interested in reading more in-depth articles in relation to knowledge management in general and Contextualise in particular, then check out my [blog](https://brettkromkamp.com/).

**Contextualise's "My maps" view**

![Contextualise's "My maps" view](https://raw.githubusercontent.com/brettkromkamp/contextualise/master/resources/my-maps.png)

**Contextualise's topic view**

![Contextualise's topic view](https://raw.githubusercontent.com/brettkromkamp/contextualise/master/resources/topic-view.png)

**Contextualise's navigable network graph view**

![Contextualise's navigable network graph view](https://raw.githubusercontent.com/brettkromkamp/contextualise/master/resources/graph-view.png)

**Contextualise's interactive 3D viewer**

![Contextualise's interactive 3D viewer](https://raw.githubusercontent.com/brettkromkamp/contextualise/master/resources/interactive-3d-viewer.png)

## Why?

I built and published my first (topic maps-based) knowledge documentation tool in 2006 which I was still using until quite recently, almost unmodified, fourteen years later. If I remember correctly, it was built with PHP version 5.2.5! Fourteen years is an eternity in software terms. Nowadays, my preferred choice for web development is [Python](https://www.python.org/) together with the [Flask](https://flask.palletsprojects.com/en/2.0.x/) web development framework. 

After fourteen years of using my own and other knowledge management tools, I have several improvements in mind for the next version (many of which are simplifications, for that matter). And perhaps one of the most important reasons for building a new tool like this is that I want it to be open source: both Contextualise (the web application) and TopicDB (the actual topic maps engine on top of which Contextualise is built &mdash; also developed by me) are licensed with the permissive open source [MIT license](https://github.com/brettkromkamp/contextualise/blob/master/LICENSE).

## Feature Support

The following provides an overview of Contextualise's existing (and planned) feature set:

### Existing Features

* Support for multiple (self-contained) topic maps
* Support for both private and public topic maps (the latter of which is not available to non-admin users until support to deal with [inappropriate content](https://github.com/brettkromkamp/contextualise/issues/9) is in place)
* Extensive support for notes including the ability to attach a note to an existing topic and convert a note into a topic
* [Markdown](https://daringfireball.net/projects/markdown/syntax)-based text editor for topic text and notes
* The ability to attach files (including images, PDFs, and so forth) to topics
* The ability to attach ([glTF](https://www.khronos.org/gltf/)-based) 3D scenes to topics with an accompanying interactive 3D scene viewer
* Powerful (semantic) associations with the ability to create typed associations with role-based members
* Flexible filtering of base names, topic occurrences and associations by scope (that is, context)
* Navigable network graph visualisation of related topics
* Auto-complete on all form fields that expect a topic reference
* Google Docs-like [collaboration](https://brettkromkamp.com/posts/contextualise-collaboration/); that is, being able to share topic maps with other Contextualise users for the purpose of collaboration in one of three ways: 1) can view, 2) can comment or 3) can edit
* Support for user-defined [knowledge paths](https://brettkromkamp.com/posts/knowledge-paths/)
* [In place topic creation](https://brettkromkamp.com/posts/in-place-topic-creation/)
* Quick association creation for frictionless topic-linking and knowledge discovery
* Associative tagging
* [Augmented Reality](https://en.wikipedia.org/wiki/Augmented_reality) (AR) support for 3D occurrences
* Syntax highlighing for numerous programming languages based on [Pygments](https://pygments.org/docs/)

### Post Version 1.0 Features

* Network graph visualisation filtering by association types
* Full-text search
* Google Maps support to see a topic within its geographical context on one hand and to be able to navigate between topics by means of a (geographic) map, on the other hand
* [Timeline](https://timeline.knightlab.com/docs/index.html) support allowing for the navigation between topics using a visual timeline component
* WikiMedia API integration to automatically enhance existing topics with relevant information from [Wikipedia](https://www.wikipedia.org/)

For a more exhaustive list of planned features take a look at Contextualise's list of [issues](https://github.com/brettkromkamp/contextualise/issues).

## Installation

Contextualise can be installed using ``pip``:

    $ pip install --upgrade contextualise

Contextualise requires Python 3.7 or higher. 

## Basic Usage
    
Create a file with the following content:

    DATABASE_FILE = "contextualise.db"

Save the file in, for example, your **home** directory with the file name ``settings.cfg``. Once you have saved the file, open a terminal and export the following environment variable:

    $ export CONTEXTUALISE_SETTINGS=$HOME/settings.cfg

The ``CONTEXTUALISE_SETTINGS`` environment variable is the path to the ``settings.cfg`` file you just created.

Flask's built-in server is not suitable for production purposes. However, it is straightforward to run Contextualise using [Gunicorn](https://gunicorn.org/), a Python [WSGI](https://en.wikipedia.org/wiki/Web_Server_Gateway_Interface) HTTP server. To run Contextualise do:

    $ gunicorn -w 2 -b 0.0.0.0:5000 contextualise.wsgi:app

This will start the application &mdash; visit ``http://127.0.0.1:5000/`` to access Contextualise.

Several users (with the roles of ``admin`` and ``user``, respectively) are created by the application. To log in as the admin user, provide the following credentials: ``admin@contextualise.dev`` (user name) and ``Passw0rd1`` (password). To log in as a non-admin user, provide the following credentials: ``user@contextualise.dev`` and ``Passw0rd1``.

For further information for properly running a flask application in production, take a look at Flask's own documentation regarding [deploying](https://flask.palletsprojects.com/en/2.0.x/deploying/).

## Install the Development Version

If you have [Git](https://git-scm.com/) installed on your system, it is possible to install the development version of Contextualise. Do:

    $ git clone https://github.com/brettkromkamp/contextualise
    $ cd contextualise
    $ git checkout develop
    $ pip install -e .

The ``pip install -e .`` command allows you to follow the development branch as it changes by creating links in the right places and installing the command line scripts to the appropriate locations.

Then, if you want to update Contextualise at any time, in the same directory do:

    $ git pull

[TopicDB](https://github.com/brettkromkamp/topic-db), the topic maps engine on top of which Contextualise is built is regularly updated. However, the version of TopicDB published on [PyPI](https://pypi.org/project/topic-db/) could lag behind. For that reason, it is recommended that you also install TopicDB directly from GitHub:

    $ pip uninstall topic-db
    $ git clone https://github.com/brettkromkamp/topic-db.git
    $ cd topic-db
    $ git checkout develop
    $ pip install -e .

Then, if you want to update TopicDB at any time, in the same directory do:

    $ git pull

Finally, to run the application in **development** mode you need to change to the project's top-level directory and set two environment variables followed by running the ``flask`` command with the ``run`` parameter:

    $ export FLASK_APP=contextualise
    $ export FLASK_ENV=development
    $ flask run

This will start the Flask development server on port 5000 &mdash; you should see something similar to the following in the terminal:

    * Serving Flask app 'contextualise' (lazy loading)
    * Environment: development
    * Debug mode: on
    [2022-02-15 18:45:29,133] INFO in __init__: Contextualise startup
    * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
    * Restarting with stat
    * Debugger is active!
    * Debugger PIN: 122-493-008
    [2022-02-15 18:45:29,866] INFO in __init__: Contextualise startup

Opening the browser and navigating to ``http://127.0.0.1:5000/`` should result in showing the application's *Welcome* page.

**The Contextualise Welcome page**

![The Contextualise Welcome page](https://raw.githubusercontent.com/brettkromkamp/contextualise/master/resources/landing-page.png)

## Documentation

Work in progress (February 2022).

## Miscellaneous

Currently, I am using Contextualise for, among others, worldbuilding purposes of the Brave Robot fictional universe including its [Codex Roboticus](https://brettkromkamp.com/posts/codex-roboticus/).

**The Codex Roboticus project**

![The Codex Roboticus project](https://raw.githubusercontent.com/brettkromkamp/contextualise/master/resources/codex-roboticus.png)

## How to Contribute

1. Check for open issues or open a fresh issue to start a discussion around a feature idea or a bug.
2. Fork [the repository](https://github.com/brettkromkamp/contextualise) on GitHub to start making your changes to the **master** branch (or branch off of it).
3. Write a test which shows that the bug was fixed or that the feature works as expected.
4. Send a pull request and bug the maintainer until it gets merged and published :)

## Final Words

I hope you enjoy using Contextualise as much as I enjoy developing it. What's more, I also genuinely hope that Contextualise can help you to improve how you organize your knowledge. If you have any suggestions, questions or critique with regards to Contextualise, I would love to hear from you.

> *I will see you again, in the place where no shadows fall*. &mdash; Ambassador Delenn, Babylon 5