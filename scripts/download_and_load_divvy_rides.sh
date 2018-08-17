#!/bin/bash

set -eu -o pipefail


WORK_DIR="${HOME}/Downloads/divvy_data/"

function safe_to_run() {
  if [ -d "$WORK_DIR" ]; then
    echo "Looks like you've already got a directory called ${WORK_DIR}"
    echo "Bailing!!"
    exit 1
  else
    mkdir -p $WORK_DIR
    echo "Making new directory: $WORK_DIR"
  fi
}

function download_and_upack_files() {

  cat <<EOF
##########################
Getting Divvy Source Files
##########################

EOF
  cd "$WORK_DIR"
  curl -O https://s3.amazonaws.com/divvy-data/tripdata/Divvy_Stations_Trips_2013.zip
  curl -O https://s3.amazonaws.com/divvy-data/tripdata/Divvy_Stations_Trips_2014_Q1Q2.zip
  curl -O https://s3.amazonaws.com/divvy-data/tripdata/Divvy_Stations_Trips_2014_Q3Q4.zip
  curl -O https://s3.amazonaws.com/divvy-data/tripdata/Divvy_Trips_2015-Q1Q2.zip
  curl -O https://s3.amazonaws.com/divvy-data/tripdata/Divvy_Trips_2015_Q3Q4.zip
  curl -O https://s3.amazonaws.com/divvy-data/tripdata/Divvy_Trips_2016_Q1Q2.zip
  curl -O https://s3.amazonaws.com/divvy-data/tripdata/Divvy_Trips_2016_Q3Q4.zip
  curl -O https://s3.amazonaws.com/divvy-data/tripdata/Divvy_Trips_2017_Q1Q2.zip
  curl -O https://s3.amazonaws.com/divvy-data/tripdata/Divvy_Trips_2017_Q3Q4.zip

  cat <<EOF

####################################################
Extracting data files to ${WORK_DIR}
####################################################

EOF

  for f in *.zip; do
    echo "Extracting to dir: ${f%.zip} for file: ${f}";
    unzip -d "${f%*.zip}" "$f";
  done

  cat <<EOF

###################################
Removing double quotes from files
###################################

Some trip files have every field quoted regardless of whether it has special characters or not (eg
a comma). If we attempt to import these double quoted CSV into postgres it will blow up as it will
have data type mismatches (eg it's expecting 1980 not "1980"). Since no fields truly require quotes
to escape special characters, we're strip double quotes from files where they appear.

EOF

  for f in $(find . -name *.csv -and ! -iname *station*); do
    if grep -q '""' "$f"; then
      echo "Looks like double quotes are used in ${f}. Removing them."
      sed -i '' 's/"//g' "$f"
    fi
  done
}

function create_ride_table_and_load() {
  cat <<EOF

####################################################
Recreating rides table and attempting to load data
####################################################

EOF

  psql -X <<INPUT
DROP TABLE IF EXISTS rides;

CREATE TABLE rides (
  trip_id bigint,
  started_at timestamp with time zone,
  ended_at timestamp with time zone,
  bike_id bigint,
  duration bigint,
  from_station_id int,
  from_station_name varchar,
  to_station_id int,
  to_station_name varchar,
  user_type varchar,
  gender varchar,
  birth_year int
)
;
INPUT

  cd "$WORK_DIR"
  for f in $(find `pwd` -name *.csv -and ! -iname *station*); do
    local row_count=`expr $(wc -l $f | xargs | cut -d' ' -f1) - 1`
    echo "Attempting to insert ${row_count} rows from ${f}"
    psql -Xc "COPY rides FROM '${f}' DELIMITER ',' CSV HEADER;"
  done
}

safe_to_run
download_and_upack_files
create_ride_table_and_load

