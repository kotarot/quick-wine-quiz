#!/bin/bash

git checkout gh-pages
git merge develop
git commit -m "Deploy to GitHub pages"
git push origin gh-pages
git checkout develop
