---
title: "Pip Make Docker and SSH Oh My"
date: 2018-07-15T22:33:27-07:00
subtitle: "Installing packages easily and securely in a docker container"
tags:
- python
- docker
- ssh
- Make
---

<!--more-->

## TLDR

this is how you use your ssh keys with Make and Docker to securely download/build Python packages 

The relevant [github gist can be found here](https://gist.github.com/knowsuchagency/e0ccd472e8ccf0cb6c378ebe467face4)

## Explanation

Docker is a great tool for building and shipping applications.
However, it can be difficult to know how to know when and how
to lock, build, and/or vendor your packages for use in a container.

You may think to download and vendor your packages locally and add
them to your container image from your local filesystem, but the
packages may not be "built" properly for the container.

Instead you try instead to build those packages from within the container
itself by adding a layer in your dockerfile i.e. `RUN pip install -r requirements.txt`
but come to find that your docker container doesn't have the proper
permissions to access the needed repositories.

The following recipe uses your local filesystem's private key and Docker's
new multi-stage build capabilities to allow you to download and vendor your packages
within a container image that will be purged once the build is complete so as to
not expose your private key in the final image.

## Makefile
```Makefile
SSH_PRIVATE_KEY=`cat ~/.ssh/id_rsa`

build-image:
	docker build . --build-arg SSH_PRIVATE_KEY="${SSH_PRIVATE_KEY}"
```

## Dockerfile
```Dockerfile
FROM python:3 as build-system

RUN pip install -U pip

COPY requirements.txt requirements.txt

### create temporary image used to download and vendor packages using private key ###
FROM build-system as intermediate

# add credentials on build
ARG SSH_PRIVATE_KEY
RUN mkdir /root/.ssh/
RUN echo "${SSH_PRIVATE_KEY}" > /root/.ssh/id_rsa
RUN chmod 600 /root/.ssh/*
RUN ssh-keyscan github.com >> /root/.ssh/known_hosts

# vendor python dependencies
RUN pip download -r requirements.txt -d /vendor/python

### create the runtime image ###
FROM build-system as runtime

# install vendored python dependencies
COPY --from=intermediate /vendor/python /vendor/python
RUN pip install /vendor/python/*
```

## Requirements.txt
```requirements.txt
git+ssh://git@github.com/{user-or-group}/{repo}.git@{optional-tag-or-commit_hash}#egg={package_name}
```