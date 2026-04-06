#!/bin/bash
cd "/Users/khan/Downloads/untitled folder 2/files/v5"
git update-ref -d HEAD
git rm -rf --cached .
git lfs install
git lfs track "data/*.bin"
git lfs track "data/*.csv"
git lfs track "data/*.json"
git add .gitattributes
git add .
git commit -m "Initialize project with data mapped via Git LFS"
git push -u origin main -f
