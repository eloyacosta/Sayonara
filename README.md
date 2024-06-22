# Sayonara

Sayonara is a tool for automating data migration form **MAD** into the new **IDEA Storage** solutions, CloudPools or CloudBucket (CloudBucket option comming soon).

There are two main software components:

1. **sayonara.py**
Which is the main CLI tool.

2. **sayonara_agent.sh**
Is a shell script wrapper that receives the routines to be executed from the sayonara CLI, via SSH protocol.
The agent will need to be installed on all the MAD brick nodes, and is not to be used manually.


# Installation

The Python CLI depends on some python modules, but there are some packages that we need to install before.
The agent will run on every brick node.

All the steps in this guide assume that you have root access to all the systems.


**Installing OS packages**

``# yum install gcc libffi-devel python-devel openssl-devel``

``# yum install python-pip``


**Installing Python packages**

``# pip install --upgrade pip``

``# pip install cryptography``

``# pip install paramiko``

``# pip install sqlite3``


**SSH key authentication**

It's necessary to create a SSH trust relationship, so the sayonara CLI is able to establish an SSH connection to the bricks without passwords.

**Clone repository**

We suggest to install the tool as root, and to clone the Git repo on /root/sayonara. If the tool is installed on other path, the config files would have to be changed accordingly.

``# cd ~``

``# git clone https://gitlab.partners.org/ez957/sayonara.git``

Please, note that the repository has to be cloned on every brick host, so the sayonara_agent.sh and .conf file are installed.

**Initialize sayonara database**

``# cd ~/sayonara``

``# mkdir .db``

``# python conf/dbinit.{env}.py``

The database initialization files have been tailored for the MAD platform. Editing the conf/dbinit.{env}.py file is required for using the tool on any other Gluster environment.


# Usage

There will be an article on the usage soon. There's a help option on the sayonara CLI though.

``# python ./sayonara.py -h``

    usage: sayonara.py [-h] {mad2cv,mad2cp,mad2cb,list,status,resume,kill} ...

    optional arguments:
      -h, --help            show this help message and exit

    Commands:
      {mad2cv,mad2cp,mad2cb,list,status,resume,kill}
        mad2cv              Starts a new transfer job from MAD to CloudVault
        mad2cp              Starts a new transfer job from MAD to CloudPools
        mad2cb              Coming Soon! Transfer job from MAD to CloudBucket
        list                List existing data transfer jobs
        status              Show the status of a job
        resume              Resume and heal and existing job
        kill                Kill a job

