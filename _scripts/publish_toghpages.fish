#!/usr/bin/env fish

set script (status -f)
set DIR (dirname $script)

cd $DIR/..

set uncommitted_changes (count (git status -s))
if math "$uncommitted_changes>0" 
    echo "The working directory is dirty. Please commit any pending changes."
    exit
end

echo "Deleting old publication"
rm -rf public
mkdir public
git worktree prune
rm -rf .git/worktrees/public/

echo "Checking out master branch into public"
git worktree add -B master public upstream/master

echo "Removing existing files"
rm -rf public/*

echo "Generating site"
hugo

echo "Updating master branch"
cd public ; git add --all ; git commit -m "Publishing to master (publish.sh)"; cd ..

# push to master
echo "pushing to master branch"
git push upstream master
echo "push succeeded"