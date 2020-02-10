#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
/* ========== TOPICDB ========== */
CREATE SCHEMA IF NOT EXISTS topicdb;


/* ========== MEMBER ========== */
CREATE TABLE IF NOT EXISTS topicdb.member (
    topicmap_identifier INT NOT NULL,
    identifier TEXT NOT NULL,
    role_spec TEXT NOT NULL,
    association_identifier TEXT NOT NULL,
    PRIMARY KEY (topicmap_identifier, identifier)
);
CREATE INDEX member_1_index ON topicdb.member (topicmap_identifier);
CREATE INDEX member_2_index ON topicdb.member (topicmap_identifier, association_identifier);


/* ========== ATTRIBUTE ========== */
CREATE TABLE IF NOT EXISTS topicdb.attribute (
    topicmap_identifier INT NOT NULL,
    identifier TEXT NOT NULL,
    parent_identifier TEXT NOT NULL,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    data_type TEXT NOT NULL,
    scope TEXT NOT NULL,
    language TEXT NOT NULL,
    PRIMARY KEY (topicmap_identifier, parent_identifier, name, scope, language)
);
CREATE INDEX attribute_1_index ON topicdb.attribute (topicmap_identifier);
CREATE INDEX attribute_2_index ON topicdb.attribute (topicmap_identifier, identifier);
CREATE INDEX attribute_3_index ON topicdb.attribute (topicmap_identifier, parent_identifier);
CREATE INDEX attribute_4_index ON topicdb.attribute (topicmap_identifier, parent_identifier, language);
CREATE INDEX attribute_5_index ON topicdb.attribute (topicmap_identifier, parent_identifier, scope);
CREATE INDEX attribute_6_index ON topicdb.attribute (topicmap_identifier, parent_identifier, scope, language);


/* ========== OCCURRENCE ========== */
CREATE TABLE IF NOT EXISTS topicdb.occurrence (
    topicmap_identifier INT NOT NULL,
    identifier TEXT NOT NULL,
    instance_of TEXT NOT NULL,
    scope TEXT NOT NULL,
    resource_ref TEXT NOT NULL,
    resource_data BYTEA,
    topic_identifier TEXT NOT NULL,
    language TEXT NOT NULL,
    PRIMARY KEY (topicmap_identifier, identifier)
);
CREATE INDEX occurrence_1_index ON topicdb.occurrence (topicmap_identifier);
CREATE INDEX occurrence_2_index ON topicdb.occurrence (topicmap_identifier, topic_identifier);
CREATE INDEX occurrence_3_index ON topicdb.occurrence (topicmap_identifier, topic_identifier, scope, language);
CREATE INDEX occurrence_4_index ON topicdb.occurrence (topicmap_identifier, topic_identifier, instance_of, scope, language);


/* ========== TOPICREF ========== */
CREATE TABLE IF NOT EXISTS topicdb.topicref (
    topicmap_identifier INT NOT NULL,
    topic_ref TEXT NOT NULL,
    member_identifier TEXT NOT NULL,
    PRIMARY KEY (topicmap_identifier, topic_ref, member_identifier)
);
CREATE INDEX topicref_1_index ON topicdb.topicref (topicmap_identifier);
CREATE INDEX topicref_2_index ON topicdb.topicref (topicmap_identifier, member_identifier);
CREATE INDEX topicref_3_index ON topicdb.topicref (topicmap_identifier, topic_ref);


/* ========== TOPIC ========== */
CREATE TABLE IF NOT EXISTS topicdb.topic (
    topicmap_identifier INT NOT NULL,
    identifier TEXT NOT NULL,
    instance_of TEXT NOT NULL,
    scope TEXT,
    PRIMARY KEY (topicmap_identifier, identifier)
);
CREATE INDEX topic_1_index ON topicdb.topic (topicmap_identifier);
CREATE INDEX topic_2_index ON topicdb.topic (topicmap_identifier, identifier, scope);
CREATE INDEX topic_3_index ON topicdb.topic (topicmap_identifier, instance_of, scope);
CREATE INDEX topic_4_index ON topicdb.topic (topicmap_identifier, scope);


/* ========== BASENAME ========== */
CREATE TABLE IF NOT EXISTS topicdb.basename (
    topicmap_identifier INT NOT NULL,
    identifier TEXT NOT NULL,
    name TEXT NOT NULL,
    topic_identifier TEXT NOT NULL,
    scope TEXT NOT NULL,
    language TEXT NOT NULL,
    PRIMARY KEY (topicmap_identifier, identifier)
);
CREATE INDEX basename_1_index ON topicdb.basename (topicmap_identifier);
CREATE INDEX basename_2_index ON topicdb.basename (topicmap_identifier, topic_identifier);
CREATE INDEX basename_3_index ON topicdb.basename (topicmap_identifier, topic_identifier, scope);
CREATE INDEX basename_4_index ON topicdb.basename (topicmap_identifier, topic_identifier, scope, language);


/* ========== TOPICMAP ========== */
CREATE SEQUENCE topicdb.topic_map_id_sequence;

CREATE TABLE IF NOT EXISTS topicdb.topicmap (
    user_identifier INT NOT NULL,
    identifier INT NOT NULL DEFAULT nextval('topicdb.topic_map_id_sequence'),
    name TEXT NOT NULL,
    description TEXT,
    image_path TEXT,
    initialised BOOLEAN DEFAULT FALSE NOT NULL,
    shared BOOLEAN DEFAULT FALSE NOT NULL,
    promoted BOOLEAN DEFAULT FALSE NOT NULL,
    PRIMARY KEY (user_identifier, identifier)
);
CREATE INDEX topicmap_1_index ON topicdb.topicmap (identifier);
CREATE INDEX topicmap_2_index ON topicdb.topicmap (shared);
CREATE INDEX topicmap_3_index ON topicdb.topicmap (promoted);

ALTER SEQUENCE topicdb.topic_map_id_sequence OWNED BY topicdb.topicmap.identifier;
EOSQL
