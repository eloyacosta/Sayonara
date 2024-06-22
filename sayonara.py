#!/usr/bin/python -Wi::DeprecationWarning
# SAYONARA 1.1b
# 10/2016
# Eloy Acosta


import argparse
import getpass
import sqlite3
import sys
import signal
import time
import paramiko as pmk
from conf.sayonara_conf import *


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def signal_handler(signal, frame):
        print bcolors.WARNING + 'WARN: Ctrl+C detected!' + bcolors.ENDC
        print bcolors.WARNING + 'WARN: All the agents will keep running, unless you kill the job' + bcolors.ENDC
        sys.exit(0)


def agent_call(user, hostname, port, command, **keyword_parameters):
    """
    This function calls the agent via SSH

    :param user:
    :param hostname:
    :param port:
    :param command:
    :param keyword_parameters:
    :return:
    """

    agent_response = {'statuscode': -1, 'info': -1}
    client = pmk.SSHClient()

    try:
        client.load_system_host_keys()
    except IOError:
        print "Cannot read keys from local known_hosts file", sys.exc_info()[0]
    except:
        print "Unexpected error:", sys.exc_info()[0]
        raise
    else:
        try:
            client.connect(hostname, port=port, username=user)
        except pmk.ssh_exception.NoValidConnectionsError:
            print bcolors.FAIL, "ERROR:", bcolors.ENDC, "connecting to the host:", hostname, "port:", port, "user:", user, \
            sys.exc_info()[0]
        except:
            print bcolors.FAIL, "ERROR:", bcolors.ENDC, "unexpected error connecting to:", hostname, sys.exc_info()[0]
        else:
            try:
                # If the agent requires an input from the user then we need to write to the remote stdin
                if 'input' in keyword_parameters:
                    # Hiding the input using if the user is asked to introduce a password
                    stdin, stdout, stderr = client.exec_command(command)
                    stdin.write(keyword_parameters['input'] + '\n')
                    stdin.flush()
                else:
                    stdin, stdout, stderr = client.exec_command(command, get_pty=False)
            except:
                print bcolors.FAIL, "ERROR:", bcolors.ENDC, "unexpected error executing command:", command, " on the host ", hostname, \
                sys.exc_info()[0]
                raise
            else:
                if stderr.readline():
                    print bcolors.FAIL, "ERROR:", bcolors.ENDC, "the remote system shell returned an error executing the command %s" % command, "on %s" % hostname, stderr.read()
                else:
                    tmpvar = stdout.read()
                    # we need to properly format the stdout string and do cast the colon separated values to integer
                    agent_response['statuscode'] = int(tmpvar.split(':')[0])
                    agent_response['info'] = int(tmpvar.split(':')[1].rstrip())
        finally:
            client.close()
    finally:
        return agent_response


def mount_vol(destservice, cv_vol, proxyname):
    """
    The function checks if the volume is mounted on the proxy and mount it in case it's not already mounted
    :param destservice:
    :param cv_vol:
    :param proxyname:
    :return statuscode, size:
    """

    dbconn = sqlite3.connect(sqlfile)
    dbconn.row_factory = sqlite3.Row
    c1 = dbconn.cursor()
    try:
        c1.execute("SELECT * FROM proxy WHERE proxyname = ?", (proxyname,))
    except sqlite3.Error as e:
        print bcolors.FAIL, "ERROR:", bcolors.ENDC, "SQLlite error(mount_cv_vol):", e.args[0], sys.exc_info()[0]
        sys.exit(1)
    else:
        proxy = c1.fetchone()
        command = "%s checkmount %s" % (agent, cv_vol)
        agent_response = agent_call(remote_user, proxy['hostname'], sshport, command)
        statuscode = agent_response['statuscode']
        space = agent_response['info']
        if statuscode == 0:  # Means the volume is already mounted. Thus, we don't have anything to do.
            return statuscode, space
        else:
            cvuser = raw_input("INPUT: Enter the username to mount the CIFS volume on the proxy: ")
            passwd = getpass.getpass("Enter the passwd: ")
            command = "%s mount %s %s %s %s" % (agent, 'cifs', cifs_servers[destservice], cv_vol, cvuser)
            agent_response2 = agent_call(remote_user, proxy['hostname'], sshport, command, input=passwd)
            statuscode2 = agent_response2['statuscode']
            space2 = agent_response2['info']
            return statuscode2, space2
    finally:
        dbconn.close()


def run_rsync_process(job_id, user, hostname, port, brickname, brickpath, sourcevol, labpath, destservice, vol, proxyname):
    """
    The function gets all the arguments to call the agent on the remote hosts, and builds the command line arguments list
    It will return the agent_status as list [ EXITCODE, info ]

    :param job_id:
    :param user:
    :param hostname:
    :param port:
    :param brickpath:
    :param sourcevol:
    :param brickname:
    :param labpath:
    :param destservice:
    :param vol
    :param proxyname:
    :return ospid:
    """

    dbconn = sqlite3.connect(sqlfile)
    dbconn.row_factory = sqlite3.Row
    c1 = dbconn.cursor()
    try:
        c1.execute("SELECT * FROM proxy WHERE proxyname = ?", (proxyname,))
    except sqlite3.Error as e:
        print bcolors.FAIL, "ERROR:", bcolors.ENDC, "SQLlite error(mount_cv_vol):", e.args[0], sys.exc_info()[0]
        sys.exit(1)
    else:
        rsyncserver = c1.fetchone()
    finally:
        dbconn.close()

    srcdir = "%s/%s" % (brickpath, labpath)
    command = "nohup %s run %s %s %s %s %s %s >/dev/null 2>&1 & echo -1:$!" % (
    agent, srcdir, destservice, vol, rsyncserver['hostname'], rsyncserver['username'], rsyncserver['passwd'])

    # Uncomment next line for debug and troubleshooting
    # print "DEBUG: running agent command: " + command
    agent_response = agent_call(user, hostname, port, command)
    ospid = agent_response['info']

    dbconn = sqlite3.connect(sqlfile)
    dbconn.row_factory = sqlite3.Row
    c1 = dbconn.cursor()
    try:
        c1.execute(
            "INSERT INTO process (jobid, ospid, user, hostname, port, brickname, brickpath) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (job_id, agent_response['info'], user, hostname, port, brickname, brickpath))
    except sqlite3.Error as e:
        print bcolors.FAIL, "ERROR:", bcolors.ENDC, "SQLlite error(run_rsync_process)", e.args[0], sys.exc_info()[0]
        sys.exit(1)
    else:
        dbconn.commit()
    finally:
        dbconn.close()
        return ospid


def resume_rsync_process(processid, user, hostname, port, brickpath, sourcevol, labpath, destservice, vol,
                         proxyname):
    """
    Resume an existing process.

    :param processid:
    :param user:
    :param hostname:
    :param port:
    :param brickpath:
    :param labpath:
    :param destservice:
    :param vol:
    :param proxyname
    :return ospid:
    """

    dbconn = sqlite3.connect(sqlfile)
    dbconn.row_factory = sqlite3.Row
    c1 = dbconn.cursor()
    try:
        c1.execute("SELECT * FROM proxy WHERE proxyname = ?", (proxyname,))
    except sqlite3.Error as e:
        print bcolors.FAIL, "ERROR:", bcolors.ENDC, "SQLlite error(mount_cv_vol):", e.args[0], sys.exc_info()[0]
        sys.exit(1)
    else:
        rsyncserver = c1.fetchone()
    finally:
        dbconn.close()

    srcdir = "%s/%s" % (brickpath, labpath)
    command = "nohup %s run %s %s %s %s %s %s >/dev/null 2>&1 & echo -1:$!" % (
    agent, srcdir, destservice, vol, rsyncserver['hostname'], rsyncserver['username'], rsyncserver['passwd'])
    agent_response = agent_call(user, hostname, port, command)

    dbconn = sqlite3.connect(sqlfile)
    dbconn.row_factory = sqlite3.Row
    c1 = dbconn.cursor()
    try:
        c1.execute("UPDATE process SET ospid = ? WHERE processid = ?", (agent_response['info'], processid))
    except sqlite3.Error as e:
        print bcolors.FAIL, "ERROR:", bcolors.ENDC, "SQLlite error(resume_rsync_process)", e.args[0], sys.exc_info()[0]
        sys.exit(1)
    else:
        dbconn.commit()
    finally:
        dbconn.close()
        ospid = agent_response['info']
        return ospid


def kill_process(ospid, user, hostname, port):
    """
    :param processid:
    :return agent_response, process:
    """
    command = "%s kill %s" % (agent, ospid)
    agent_call(user, hostname, port, command)


def check_process(ospid, user, hostname, port):
    """
    :param process:
    :return pstatus, ospid:
    """

    command = "%s check %s" % (agent, ospid)
    agent_response = agent_call(user, hostname, port, command)
    pstatus = agent_response['statuscode']
    ospid = agent_response['info']

    return pstatus, ospid


def get_job_processes(jobid):
    """
    :param jobid:
    :return database cursor:
    """
    dbconn = sqlite3.connect(sqlfile)
    dbconn.row_factory = sqlite3.Row
    c1 = dbconn.cursor()

    try:
        c1.execute("SELECT * FROM process,job WHERE process.jobid = job.jobid AND job.jobid = :jobid", (jobid,))
    except sqlite3.Error as e:
        print bcolors.FAIL, "ERROR:", bcolors.ENDC, "SQLlite error(get_job_processes):", e.args[0], sys.exc_info()[0]
        sys.exit(1)
    else:
        resulset = c1.fetchall()
        return resulset
    finally:
        dbconn.close()


def get_job_list(status):
    """
    :param status:
    :return:
    """

    dbconn = sqlite3.connect(sqlfile)
    dbconn.row_factory = sqlite3.Row
    c1 = dbconn.cursor()

    jobstatus = {
        'active': [0],  # There's at least 1 process running
        'finished': [1],  # All processes finished correctly
        'stopped': [2],  # All processes are stopped/killed
        'warn': [3],  # There might be one or more processes with problems
        'inconsistent': [5],  # There are processes that never run
        'all': [0, 1, 2, 3, 5],
    }

    query = 'SELECT * FROM job WHERE status IN (%s)' % ','.join('?' for i in jobstatus[status])

    try:
        c1.execute(query, jobstatus[status])
    except sqlite3.Error as e:
        print bcolors.FAIL, "ERROR:", bcolors.ENDC, "SQLlite error(get_job_list):", e.args[0], sys.exc_info()[0]
        sys.exit(1)
    else:
        resulset = c1.fetchall()
        return resulset
    finally:
        dbconn.close()


def run_rsync_job(gluster_vol, labpath, destservice, vol, proxyname, pdegree):
    """
    Will run a transfer job from MAD | MADR to CloudVault.
    The CV share has to be previously mounted

    :param gluster_vol:
    :param labpath:
    :param destservice:
    :param vol:
    :param proxyname:
    :param pdegree:
    :return:
    """

    # Register the SIGINT to trap Ctr+C
    signal.signal(signal.SIGINT, signal_handler)
    # The volume has to be mounted on the proxy
    print "==> Checking the volume %s is mounted on the proxy %s" % (vol, proxyname)
    statuscode, size = mount_vol(destservice, vol, proxyname)
    if statuscode == 0:
        print "==> The volume mounted and the space available is %s Bytes" % size
    else:
        print bcolors.FAIL, "ERROR:", bcolors.ENDC, "Failed mounting the volume", vol, "on", proxyname
        print bcolors.FAIL, "Job execution cancelled", bcolors.ENDC
        sys.exit(1)

    # We create a dictionary to prevent SQL injection provide with greater flexibility
    # TODO: change the dictionary and the initialization data so it matches glusterfs vol names
    madvol = {
        'store': 'store',
        'replicated2': 'replicated2',
        'afr': 'afr',
        'store.1-2': 'store.1-2',
        'store.2-2': 'store.2-2',
    }

    dbconn = sqlite3.connect(sqlfile)
    dbconn.row_factory = sqlite3.Row
    c1 = dbconn.cursor()

    try:
        c1.execute(
            "SELECT  madvol.*, madbrick.* FROM madvol, madbrick where madbrick.volid = madvol.volid AND madvol.volname = ? ORDER BY madbrick.brickid ASC",
            (madvol[gluster_vol],))
        resultset = c1.fetchall()
    except sqlite3.Error as e:
        print bcolors.FAIL, "ERROR:", bcolors.ENDC, "SQLlite error(run_rsync_job)", e.args[0], sys.exc_info()[0]
        sys.exit(1)
    else:
        # We need to insert and commit first. Otherwise, the FK integrity check will fail.
        try:
            c1.execute(
                "insert into job (sourcevol, volid, labpath, dest, destservice, proxyname, status, pdegree) values(?, ?, ?, ?, ?, ?, ?, ?)",
                (madvol[gluster_vol], resultset[0]['volid'], labpath, vol, destservice, proxyname, 0, pdegree))
        except sqlite3.Error as e:
            print bcolors.FAIL, "ERROR:", bcolors.ENDC, "SQLlite error(run_rsync_job):", e.args[0], sys.exc_info()[0]
            sys.exit(1)
        else:
            jobid = c1.lastrowid
            dbconn.commit()
            i = 0
            pcount = 0
            print bcolors.BOLD + '==> Parallel degree is: %s' % pdegree + bcolors.ENDC

            for row in resultset:
                # If vol_type is replicated I have to skip every other brick
                if row['voltype'] == 'replicated' and i % 2 != 0:
                    i += 1
                    continue
                while pcount >= pdegree != 0:  # pdegree = 0 means no limit
                    print bcolors.BOLD + '==> Checking if there is a new slot availiable...' + bcolors.ENDC
                    pstatus = check_job_status(jobid, quiet=True)
                    if pstatus['#running'] < pdegree:
                        print bcolors.BOLD + '==> Parallel degree is %s and the # of running processes is %s. There is one slot available!' % (pdegree, pstatus['#running']) + bcolors.ENDC
                        break
                    else:
                        print '==> Parallel degree is %s and the # of running processes is %s. No slots available' % (pdegree, pstatus['#running'])
                        print '==> Waiting %s seconds ... ' % checktime
                    time.sleep(checktime)

                ospid = run_rsync_process(jobid, remote_user, row['hostname'], sshport, row['brickname'], row['brickpath'],
                                          madvol[gluster_vol],
                                          labpath, destservice, vol, proxyname)
                print "==> Process with OS PID", ospid, bcolors.BOLD, "running on", bcolors.ENDC, row['hostname'], row['brickname']
                pcount += 1
                i += 1
                check_job_status(jobid, quiet=False)

            print bcolors.BOLD + "==> DONE. All the sync processes were submitted..." + bcolors.ENDC

    finally:
        dbconn.close()


def update_job_status(jobid, jobstatus):
    """
    :param jobid:
    :param jobstatus:
    :return:
    """

    dbconn = sqlite3.connect(sqlfile)
    dbconn.row_factory = sqlite3.Row
    c1 = dbconn.cursor()

    try:
        c1.execute("UPDATE job SET status = ?  WHERE jobid = ?", (jobstatus, jobid,))
    except sqlite3.Error as e:
        print bcolors.FAIL, "ERROR:", bcolors.ENDC, "SQLlite error(update_job_status):", e.args[0], sys.exc_info()[0]
    else:
        dbconn.commit()
    finally:
        dbconn.close()


def check_job_status(jobid, quiet=False):
    """
    Function will return a job list and the status of each one
    :param jobid:
    :param quiet:
    :return jobsummary:
    """

    global jobsummary
    dbconn = sqlite3.connect(sqlfile)
    dbconn.row_factory = sqlite3.Row
    c1 = dbconn.cursor()
    try:
        c1.execute("SELECT * FROM job WHERE jobid = ?", (jobid,))
    except sqlite3.Error as e:
        print bcolors.FAIL, "ERROR:", bcolors.ENDC, "SQLite error (job_kill):", e.args[0], sys.exc_info()[0]
    else:
        job = c1.fetchone()
        if job is None:
            print bcolors.FAIL, "ERROR:", bcolors.ENDC, "JobId %s doesn't exist" % jobid
            sys.exit(1)
        else:
            jobsummary = {'gstatus': int(0), '#running': int(0), '#finished': int(0), '#stopped': int(0),
                          '#total': int(0)}
            pslist = {}
            for process in get_job_processes(jobid):
                jobsummary['#total'] += 1
                statuscode, ospid = check_process(process['ospid'], process['user'], process['hostname'],
                                                  process['port'])
                pslist[process['processid']] = statuscode
                if statuscode == 0:
                    jobsummary['#running'] += 1
                elif statuscode == 1:
                    jobsummary['#finished'] += 1
                elif statuscode == 2:
                    jobsummary['#stopped'] += 1
                else:
                    print bcolors.FAIL, "ERROR:", bcolors.ENDC, "Can't get status for agent ID", process['processid']

            if jobsummary['#stopped'] >= 1 and jobsummary['#stopped'] != jobsummary['#total']:
                jobsummary['gstatus'] = 'warn'
                update_job_status(jobid, 3)
            elif jobsummary['#running'] > 0 and jobsummary['#stopped'] == 0:
                jobsummary['gstatus'] = 'active'
                update_job_status(jobid, 0)
            elif jobsummary['#finished'] == jobsummary['#total']:
                jobsummary['gstatus'] = 'finished'
                update_job_status(jobid, 1)
            elif jobsummary['#stopped'] == jobsummary['#total']:
                jobsummary['gstatus'] = 'stopped'
                update_job_status(jobid, 2)
            else:
                jobsummary['gstatus'] = 'inconsistent'
                update_job_status(jobid, 5)

            if quiet is False:
                print "----"
                print "JOB SUMMARY FOR", bcolors.BOLD, "JobID", job['jobid'], bcolors.ENDC, "launched on", job['stimestamp'], "GMT"
                print bcolors.BOLD + "*** DETAILS >>" + bcolors.ENDC, " gluster_vol:", job['sourcevol'], "| basepath:", \
                    job['labpath'], "| dest_vol:", job['dest'], "| dest_service:", job['destservice']
                print bcolors.BOLD + "*** STATUS  >>" + bcolors.ENDC, \
                    bcolors.OKBLUE, jobsummary['#running'], "agents running", bcolors.ENDC, "|", \
                    bcolors.OKGREEN, jobsummary['#finished'], "finished", bcolors.ENDC, "|", \
                    bcolors.FAIL, jobsummary['#stopped'], "stopped/killed" + bcolors.ENDC
                print "----"
    finally:
        dbconn.close()
    return jobsummary


def job_summary(status):
    """
    This function is just for printing the summary of the jobs that match a given status

    :param status:
    """
    job_list = get_job_list(status)

    for job in job_list:
        check_job_status(job['jobid'], quiet=False)


def job_kill(jobid):
    """
    This function will use get_job_process() to get the list of processes along with the status.
    Then will call agent_call() with the required arguments to run the processes that need to be resumed.
    If everything goes well, have to update the DB.

    :param job_id:
    :return:
    """

    dbconn = sqlite3.connect(sqlfile)
    dbconn.row_factory = sqlite3.Row
    c1 = dbconn.cursor()
    try:
        c1.execute("SELECT * FROM job WHERE jobid = ?", (jobid,))
    except sqlite3.Error as e:
        print bcolors.FAIL, "ERROR:", bcolors.ENDC, "SQLite error (job_kill):", e.args[0], sys.exc_info()[0]
    else:
        job = c1.fetchone()
        if job is None:
            print bcolors.FAIL, "ERROR:", bcolors.ENDC, "JobId %s doesn't exist" % jobid
            sys.exit(1)
        else:
            for process in get_job_processes(jobid):
                pstatus, ospid = check_process(process['ospid'], process['user'], process['hostname'], process['port'])
                if pstatus == 0:
                    print "==> Killing agent with ID %s and OSPID %s on %s ..." % \
                          (process['processid'], process['ospid'], process['hostname'])
                    kill_process(process['ospid'], process['user'], process['hostname'], process['port'])
                    new_pstatus, new_ospid = check_process(process['ospid'], process['user'], process['hostname'],
                                                           process['port'])
                    if new_pstatus == 2:
                        print bcolors.BOLD + "==> Killed!" + bcolors.ENDC
                    else:
                        print bcolors.FAIL, "ERROR:", bcolors.ENDC, "Couldn't kill agent with OSPID %s. Exit code %s", (
                        new_ospid, new_pstatus)
                elif pstatus == 1:
                    print "==> Agent ID %s" % process['processid'], "on", process[
                        'hostname'], "finished...", bcolors.WARNING, "Nothing to do!", bcolors.ENDC
                elif pstatus == 2:
                    print "==> Agent ID %s" % process['processid'], "on", process[
                        'hostname'], "was already killed...", bcolors.WARNING, "Nothing to do!", bcolors.ENDC
                else:
                    print bcolors.FAIL, "ERROR:", bcolors.ENDC, "Can't get status for agent ID", process['processid']

            # Now let's check the job status and get a nice summary
            print "==> Checking job integrity..."
            check_job_status(jobid, quiet=False)
    finally:
        dbconn.close()


def find_element_in_list(brick, mylist):
    i = 0
    for row in mylist:
        if brick == row['brickname']:
            return i
        i += 1
    return False


def job_resume(jobid):
    """
    This function will use get_job_process() to get the list of processes along with the status.
    Then will call agent_call() with the required arguments to run the procecesses that need to be resumed.
    If everything goes well, have to update the DB.

    :param jobid:
    :return:
    """

    # Register the SIGINT to trap Ctr+C
    signal.signal(signal.SIGINT, signal_handler)

    dbconn = sqlite3.connect(sqlfile)
    dbconn.row_factory = sqlite3.Row
    c1 = dbconn.cursor()

    try:
        c1.execute("SELECT * FROM job WHERE jobid = ?", (jobid,))
    except sqlite3.Error as e:
        print bcolors.FAIL, "ERROR:", bcolors.ENDC, "SQLite error (job_resume):", e.args[0], sys.exc_info()[0]
    else:
        job = c1.fetchone()
        if job is None:
            print bcolors.FAIL, "ERROR:", bcolors.ENDC, "JobId %s doesn't exist" % jobid
            sys.exit(1)
        else:
            # The volume has to be mounted on the proxy before resuming the Job
            print "==> Checking the volume %s is mounted on the proxy" % job['dest']
            statuscode, size = mount_vol(job['destservice'], job['dest'], job['proxyname'])
            if statuscode == 0:
                print "==> The volume mounted and the space available is %s Bytes" % size
            else:
                print bcolors.FAIL, "ERROR:", bcolors.ENDC, "Failed mounting the volume", job['dest'], "on", job['proxyname']
                print bcolors.FAIL, "Job execution cancelled", bcolors.ENDC
                sys.exit(1)

            c1.execute("SELECT  madvol.*, madbrick.* FROM madvol, madbrick where madbrick.volid = madvol.volid AND "
                       "madvol.volid = ? ORDER BY madbrick.brickid ASC", (job['volid'],))
            allbricks = c1.fetchall()
            submitted_jobs = get_job_processes(jobid)
            i = 0
            pcount = 0
            print bcolors.BOLD + '==> The parallel degree is: %s' % job['pdegree'] + bcolors.ENDC

            for brick in allbricks:
                # If vol_type is replicated I have to skip every other brick
                if brick['voltype'] == 'replicated' and i % 2 != 0:
                    i += 1
                    continue

                while pcount >= job['pdegree'] != 0:  # pdegree = 0 means no limit
                    print bcolors.BOLD + '==> Checking if there is a new slot availiable...' + bcolors.ENDC
                    pstatus = check_job_status(jobid, quiet=True)
                    if pstatus['#running'] < job['pdegree']:
                        print bcolors.BOLD + '==> Parallel degree is %s and the # of running processes is %s. ' \
                                             'There is one slot available!' % (job['pdegree'], pstatus['#running']) + bcolors.ENDC
                        break
                    else:
                        print '==> Parallel degree is %s and the # of running processes is %s. No slots available' %\
                              (job['pdegree'], pstatus['#running'])
                        print '==> Waiting %s seconds ... ' % checktime
                    time.sleep(checktime)

                myindex = find_element_in_list(brick['brickname'], submitted_jobs)
                if myindex is not False:  # Means maybe there's an agent already running for that brick
                    pstatus, ospid = check_process(submitted_jobs[myindex]['ospid'], submitted_jobs[myindex]['user'], submitted_jobs[myindex]['hostname'], submitted_jobs[myindex]['port'])
                    if pstatus == 0:
                        print "==> Agent ID %s is running already. Nothing to do." % submitted_jobs[myindex]['processid']
                    elif pstatus == 1:
                        print "==> Agent ID %s finished. Nothing to do." % submitted_jobs[myindex]['processid']
                    elif pstatus == 2:
                        print "==> Resuming agent ID %s" % submitted_jobs[myindex]['processid'], "on", submitted_jobs[myindex]['hostname']
                        resume_rsync_process(submitted_jobs[myindex]['processid'], submitted_jobs[myindex]['user'],
                                             submitted_jobs[myindex]['hostname'], submitted_jobs[myindex]['port'],
                                             submitted_jobs[myindex]['brickpath'], submitted_jobs[myindex]['sourcevol'],
                                             submitted_jobs[myindex]['labpath'],job['destservice'], submitted_jobs[myindex]['dest'],
                                             submitted_jobs[myindex]['proxyname'])
                        print bcolors.BOLD + "==> Resumed!" + bcolors.ENDC
                    else:
                        print bcolors.FAIL, "ERROR:", bcolors.ENDC, "Can't get status for agent ID", submitted_jobs[myindex]['processid']
                else:
                    ospid = run_rsync_process(jobid, remote_user, brick['hostname'], sshport, brick['brickname'],
                                              brick['brickpath'], job['sourcevol'], job['labpath'], job['destservice'],
                                              job['dest'], job['proxyname'])
                    print "==> Process with OS PID", ospid, bcolors.BOLD, "running on", bcolors.ENDC, brick['hostname'], brick['brickname']

                pcount += 1
                i += 1
    finally:
        dbconn.close()
        print bcolors.BOLD + "==> DONE. All the sync processes were submitted..." + bcolors.ENDC
        print "==> Checking job integrity..."
        check_job_status(jobid, quiet=False)


# Menu options and main functions

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(title='Commands', dest='subcommand_name')

mad2cv = subparsers.add_parser('mad2cv', help='Starts a new transfer job from MAD to CloudVault')
mad2cv.add_argument("gluster_vol", help="Gluster volume you want to transfer data from", nargs=1,
                    choices=['store', 'afr', 'replicated2'])
mad2cv.add_argument("lab_name", help="The name of the lab or the MAD customer", nargs=1)
mad2cv.add_argument("cv_vol", help="The name of the destination CloudVault volume", nargs=1)
mad2cv.add_argument("proxy", help="The Gateway to use as proxy server", nargs=1,
                    choices=['mad-store1', 'mad-replicated1'])
mad2cv.add_argument("-p", help="The number of parallel processes", nargs=1, type=int, choices=range(0, 16), default=[0])

mad2cp = subparsers.add_parser('mad2cp', help='Starts a new transfer job from MAD to CloudPools')
mad2cp.add_argument("gluster_vol", help="Gluster volume you want to transfer data from", nargs=1,
                    choices=['store', 'afr', 'replicated2', 'store.1-2', 'store.2-2'])
mad2cp.add_argument("lab_name", help="The name of the lab or the MAD customer", nargs=1)
mad2cp.add_argument("cv_vol", help="The name of the destination CIFS volume on Isilon", nargs=1)
mad2cp.add_argument("proxy", help="The Gateway to use as proxy server", nargs=1,
                    choices=['mad-store1', 'mad-replicated1'])
mad2cp.add_argument("-p", help="The number of parallel processes", nargs=1, type=int, choices=range(0, 16), default=[0])
mad2cp.add_argument("-s", help="The Isilon server to send the data", nargs=1, choices=['CP', 'CP1', 'CP2', 'CP3'], default=['CP'])

mad2cb = subparsers.add_parser('mad2cb', help='Coming Soon! Transfer job from MAD to CloudBucket')
mad2cb.add_argument("gluster_vol", help="The Gluster volume you want to transfer data from", nargs=1,
                    choices=['store', 'afr', 'replicated2'])
mad2cb.add_argument("lab_name", help="The name of the lab or customer on MAD", nargs=1)
mad2cb.add_argument("cb_accesskey", help="CloudBucket ACCESS_KEY", nargs=1)
mad2cb.add_argument("cb_secretkey", help="CloudBucket SECRET_KEY", nargs=1)
mad2cb.add_argument("bucket_name", help="The name of the destination bucket", nargs=1)
mad2cb.add_argument("-p", help="The number of parallel processes", nargs=1, type=int, choices=range(0, 16), default=[0])

list = subparsers.add_parser('list', help='List existing data transfer jobs')
list.add_argument('status', nargs=1, choices=['active', 'stopped', 'finished', 'all'], default='active',
                  help='show the process list that matches the given status')

status = subparsers.add_parser('status', help='Show the status of a job')
status.add_argument("jobid", help="The ID of the job", nargs=1)

resume = subparsers.add_parser('resume', help='Resume and heal and existing job')
resume.add_argument('id', type=int, help='Job_Id')

kill = subparsers.add_parser('kill', help='Kill a job')
kill.add_argument('id', type=int, help='Job_Id')

args = parser.parse_args()

if args.subcommand_name == 'mad2cv':
    # See config file to find the server for CV and CP
    run_rsync_job(args.gluster_vol[0], args.lab_name[0], 'CV', args.cv_vol[0], args.proxy[0], args.p[0])
    print 'el valor de paralale es: %s' % args.parallel[0]
elif args.subcommand_name == 'mad2cp':
    run_rsync_job(args.gluster_vol[0], args.lab_name[0], args.s[0], args.cv_vol[0], args.proxy[0], args.p[0])
elif args.subcommand_name == 'mad2cb':
    print "Function not implemented yet. Coming soon!"
elif args.subcommand_name == 'list':
    job_summary(args.status[0])
elif args.subcommand_name == 'status':
    check_job_status(args.jobid[0])
elif args.subcommand_name == 'resume':
    job_resume(args.id)
elif args.subcommand_name == 'kill':
    job_kill(args.id)
elif args.subcommand_name == 'mount':
    mount_vol(args.cv_vol)
