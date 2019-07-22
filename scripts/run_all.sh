#!/bin/sh
set -euo pipefail

function usage() {
    echo "
usage:   run_all.sh [options]
options:
  -c    RUN makeConfig.py
  -s    RUN svSupport.py

  -v    path to variants
  -b    path to bams
  -o    path to output dir
  -p    purity file
  -h    show this message
"
}

function getBase(){
  stem=$(basename "$1" )
  name=$(echo $stem | cut -d '_' -f 1)
  echo $name
}

bamdir=/Volumes/perso/Analysis/Bwa
variants=/Users/Nick_curie/Desktop/parserTest/filtered4/summary/merged
out_dir=/Users/Nick_curie/Desktop/script_test/svSupport/out
purity=/Users/Nick_curie/Desktop/script_test/svSupport/data/tumour_purity.txt
script_bin=/Users/Nick_curie/Desktop/script_test/svSupport
makeConfig=0
svSupport=0

while getopts 'v:b:o:p:hcs' flag; do
  case "${flag}" in
    v)  variants="$OPTARG" ;;
    b)  bamdir="$OPTARG" ;;
    o)  out_dir="$OPTARG" ;;
    p)  purity="$OPTARG" ;;
    c)  makeConfig=1 ;;
    s)  svSupport=1 ;;
    h)  usage
        exit 0 ;;
  esac
done

if [[ $makeConfig -eq 0 && $svSupport -eq 0 ]]
then
  usage
  exit 0
fi

if [[ $makeConfig -eq 1 ]]
then

  for f in $variants/*_annotated_SVs.txt
  do
    sample=$(getBase $f)
    echo "Making config for $sample"
    python $script_bin/scripts/makeConfig.py -b $bamdir -p $purity -v $f -s $sample
  done
fi

if [[ $svSupport -eq 1 ]]
then
  for c in *_config.txt
  do
    sample=$(getBase $c)
    echo "Running svSupport for $sample:"
    echo "python $script_bin/svSupport/svSupport.py -c $c -o $out_dir/$sample"
    python $script_bin/svSupport/svSupport.py -c $c -o "$out_dir/$sample"
  done
fi
