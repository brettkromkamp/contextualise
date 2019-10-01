Contextualise by Brett Kromkamp
===============================

``Contextualise`` is a simple and flexible tool particularly suited for organising information-heavy projects and
activities consisting of (semi) unstructured and widely diverse data and information resources --- think of
investigative journalism, personal and professional research projects, `world building`_ (for books, movies or computer
games) and many kinds of hobbies.

.. image:: resources/topic-view.png
   :alt: Contextualise's topic view

``Contextualise``'s main dependency is `TopicDB`_, an open source `topic maps`_-based graph library. Topic maps provide
a way to describe complex relationships between abstract concepts and real-world (information) resources.

Why?
----

I built and published my first knowledge documentation tool in 2007 which I was still using until very recently, almost
unmodified, twelve years later. If I remember correctly, it was built with `PHP version 5.2.5`_! Twelve years is an
eternity in software terms. Nowadays, my preferred choice for web development is `Python`_ together with the `Flask`_
web development framework. What's more, after twelve years of using my own and other knowledge management tools, I have
several improvements in mind for the next version (many of which are simplifications, for that matter). And perhaps one
of the most important reasons for building a new tool like this is that I want it to be open source: both
``Contextualise`` (the web application) and ``TopicDB`` (the actual topic maps engine on top of which ``Contextualise``
is built --- also written by me) are licensed with the permissive open source `MIT license`_.

Feature Support
---------------

Pending.

Install the Development Version
-------------------------------

``Contextualise`` officially supports Python 3.6–3.7.

If you have `Git <https://git-scm.com/>`_ installed on your system, it is possible to install the development version
of ``Contextualise``.

Certain build prerequisites need to met including the presence of a C compiler, the Python
header files, the ``libpq`` header files and the ``pg_config`` program as outlined, here: `Build
prerequisites <http://initd.org/psycopg/docs/install.html#build-prerequisites>`_.

Then do::

    $ git clone https://github.com/brettkromkamp/contextualise
    $ cd contextualise
    $ pip install -e .

The ``pip install -e .`` command allows you to follow the development branch as it changes by creating links in the
right places and installing the command line scripts to the appropriate locations.

Then, if you want to update ``Contextualise`` at any time, in the same directory do::

    $ git pull

After having installed Contextualise, you would have to separately install and configure the PostgreSQL database. Brief
instructions on how to do so are provided, here: `Setting up the TopicDB
database <https://gist.github.com/brettkromkamp/87aaa99b056578ff1dc23a43a49aca89>`_. You need to ensure that the
database username, password and database name match with the ``settings.ini`` file in the project's root folder.

First-Time Use
--------------

Pending.

Tutorial
--------

Pending.

Documentation
-------------

Pending.

How to Contribute
-----------------

#. Check for open issues or open a fresh issue to start a discussion around a feature idea or a bug.
#. Fork `the repository`_ on GitHub to start making your changes to the **master** branch (or branch off of it).
#. Write a test which shows that the bug was fixed or that the feature works as expected.
#. Send a pull request and bug the maintainer until it gets merged and published. :) Make sure to add yourself to AUTHORS_.

.. _topic maps: https://msdn.microsoft.com/en-us/library/aa480048.aspx
.. _world building: https://en.wikipedia.org/wiki/Worldbuilding
.. _TopicDB: https://github.com/brettkromkamp/topic-db
.. _Knowledge Management Using Topic Maps: http://quesucede.com/page/show/id/frontpage
.. _PHP version 5.2.5: http://php.net/ChangeLog-5.php#5.2.5
.. _Python: https://www.python.org/
.. _Flask: http://flask.pocoo.org/docs/1.0/
.. _MIT license: https://github.com/brettkromkamp/contextualise/blob/master/LICENSE
.. _the repository: https://github.com/brettkromkamp/contextualise
.. _AUTHORS: https://github.com/brettkromkamp/contextualise/blob/master/AUTHORS.rst
