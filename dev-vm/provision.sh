#!/bin/bash
echo I am provisioning...
yum -y install git cifs-utils xinetd
sudo su root -c "cp /tmp/.gitconfig /root"
sudo su root -c "cp /tmp/rsyncd.conf /etc"
sudo su root -c "cp /tmp/rsyncd.secrets /etc"
sudo su root -c "unalias cp"
sudo su root -c "cp /tmp/rsync /etc/xinetd.d/rsync"
sudo su root -c "chmod 600 /etc/rsyncd.secrets"
sudo su root -c "/etc/init.d/xinetd restart"
sudo su root -c "rm -f /root/.ssh/id_rsa /root/.ssh/id_rsa.pub"
sudo su root -c "ssh-keygen -q -P \"\" -f /root/.ssh/id_rsa"
sudo su root -c "cp /tmp/host.pubkey /root/.ssh/authorized_keys"
sudo su root -c "cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys"
sudo su root -c "mkdir -p /mnt/sayonara/"
echo provisioning demo files...
sudo su root -c "chmod 777 -R /mnt/brick*"
rsync --daemon