#!/usr/bin/env bash

psql $DATABASE_URL -a -f database.sql
