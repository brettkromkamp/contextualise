FROM python:3

# Metadata
LABEL \
  app.name="Contextualise" \
  app.description="A simple and flexible tool particularly suited for organising information-heavy projects and activities consisting of unstructured and widely diverse data and information resources" \
  app.license="MIT License" \
  app.license.url="https://github.com/brettkromkamp/contextualise/blob/master/LICENSE" \
  app.repo.url="https://github.com/brettkromkamp/contextualise" \
  app.authors="Brett Kromkamp <@brettkromkamp>"

# Fetch just the dependencies, caches on the contents of requirements.txt
WORKDIR /usr/src/app
COPY ./requirements.txt ./
RUN pip install --user git+https://github.com/brettkromkamp/topic-db.git \
 && pip install --user -r requirements.txt

# Copy in the rest of the project and dependencies
COPY . .
RUN test -f settings.ini || cp settings-docker-sample.ini settings.ini

# Config for python and the app
ENV \
  PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  FLASK_APP=contextualise \
  FLASK_ENV=production \
  PATH=$PATH:/root/.local/bin

# Execute via gunicorn by default
CMD ["gunicorn", "-b", "0.0.0.0:5000", "contextualise.wsgi:app"]
EXPOSE 5000
