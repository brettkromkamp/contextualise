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

# Install basic requirements
WORKDIR    /contextualise
COPY       requirements.txt ./
RUN        pip install -r requirements.txt

# Install Contextualise from the source code
COPY       . ./
RUN        python setup.py install
RUN        pip install -e .

RUN        apt update && apt install -y gcc git python-dev libpq-dev

RUN        git clone https://github.com/psycopg/psycopg2 && \
           cd psycopg2

ENTRYPOINT ["contextualize"]