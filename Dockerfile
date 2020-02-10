FROM       python:3

# Add some metadata
LABEL      app.name="Contextualise" \
           app.description="A simple and flexible tool particularly suited for organising information-heavy projects and activities consisting of unstructured and widely diverse data and information resources" \
           app.license="MIT License" \
           app.license.url="https://github.com/brettkromkamp/contextualise/blob/master/LICENSE" \
           app.repo.url="https://github.com/brettkromkamp/contextualise" \
           app.authors="Brett Kromkamp <@brettkromkamp>"

# Enable unbuffered STDOUT logging
ENV        PYTHONUNBUFFERED=1

RUN        git clone https://github.com/psycopg/psycopg2 && \
           cd psycopg2 && \
           python setup.py build && \
           python setup.py install

# Install Contextualise from the source code
COPY       . ./

# Install requirements
WORKDIR    /contextualise
COPY       . ./
RUN        pip install --user -r requirements.txt
RUN        pip install --user ./

ENV        FLASK_APP contextualise
ENV        FLASK_ENV development
