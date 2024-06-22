# CONFIG VARS

sqlfile = '.db/sayonara.db'
remote_user = 'root'
sshport = int(22)
agent = '~/sayonara/sayonara_agent.sh'


# keynames must match the values provided to run_rsync_job() - e.g. by the argument subparsers
# CP = Isilon / CloudPools
# CV = CloudVault

cifs_servers = {
    'CP': 'xyz.domain.com',
    'CV': 'xyz.domain.com',
    }

# The number of seconds to wait between checks when the parallel degree is set
checktime = 10