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

RUN        apt update && apt install -y gcc git python-dev libpq-dev postgresql postgresql-contrib

USER       postgres

# Create PostgreSQL role named "docker" with "docker" as the password
# Then create a database "docker" owned by the "docker" role.
RUN        /etc/init.d/postgresql start && \
           psql --command "CREATE USER docker WITH SUPERUSER PASSWORD 'docker';" && \
           createdb -O docker docker # && \
           # psql -h localhost -U docker -d docker -a -f topicmap-definition.sql

RUN        git clone https://github.com/psycopg/psycopg2 && \
           cd psycopg2 && \
           python setup.py build && \
           python setup.py install

# Install Contextualise from the source code
COPY       . ./

# Install basic requirements
WORKDIR    /contextualise
COPY       . ./
RUN        pip install --user -r requirements.txt && \
           python setup.py install

RUN        export FLASK_APP=contextualise && \
           export FLASK_ENV=development && \
           flask run

#ENTRYPOINT ["bash"]