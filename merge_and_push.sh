#!/bin/bash

git checkout master;
git merge develop;
git checkout develop;
git push origin master develop;
