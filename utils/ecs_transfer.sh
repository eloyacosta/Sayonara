#!/bin/bash

PARALLEL=/root/data_transfers/parallel/bin/parallel
S3CMD=/usr/bin/s3cmd


PDEGREE=4

if [ $# -lt 4 ] || [  $1 = "-help" ]
then
    echo "Usage: $0 {upload|download} local_dir bucket_name/<path> index_filename"
    exit 1
fi

case "$1" in
    "upload")
    find "$2" -type f | tee "$4" | "$PARALLEL" --no-notice --jobs "$PDEGREE" "$S3CMD" put -p "{}" s3://"$3"{} ;
    "$S3CMD" put -p "$4" s3://"$3"/
    ;;
    "download")

    echo "DOWNLOADING INDEX FILE ..."
    "$S3CMD" get s3://"$3"/"$4" || echo "ERROR TRYING TO INDEX FROM CLOUD, LOCAL DIR..."

    echo "CREATING DIRECTORY STRUCTURE IN THE LOCAL DIR $2 ..."
    for i in $(cat "$4"); do echo $(dirname $i); done |sort -u| for v in $(cat); do mkdir -p "$2/$v"; done

    echo "DOWNLOADING OBJECTS FROM BUCKET $3 ..."
    cat "$4" | "$PARALLEL" --no-notice --jobs "$PDEGREE" "$S3CMD" get --no-check-md5 s3://"$3"{} "$2"{}
    ;;

    *)
    ;;
esac