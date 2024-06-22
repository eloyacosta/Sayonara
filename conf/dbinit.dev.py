from sayonara_conf import *
from dbschema import *


def db_init(sqlfile):

    dbconn = sqlite3.connect(sqlfile)
    c1 = dbconn.cursor()

    print('*** Initializing Database...')

    try:
        # Populate db with config data

        vol = [(1, 'store', 'distributed'),
               (2, 'afr', 'replicated'),
               (3, 'store.1-2', 'distributed'),
               (4, 'store.2-2', 'distributed'),
               (5, 'afr.1-2', 'replicated'),
               (6, 'afr.2-2', 'replicated'),
               ]

        c1.executemany('INSERT INTO madvol (volid, volname, voltype) VALUES (?,?,?)', vol)

        """
        Heads up: it's really important to provision the bicks in the correct order as they are listed by the
        'gluster vol info' command
        """
        madbrick = [(1,'brick01', 'dev-vm', '/mnt/brick1/store'),
                    (1,'brick02', 'dev-vm', '/mnt/brick2/store'),
                    (1,'brick03', 'dev-vm', '/mnt/brick3/store'),
                    (1,'brick04', 'dev-vm', '/mnt/brick4/store'),
                    (2,'brick01', 'dev-vm', '/mnt/brick1/store-replicated'),
                    (2,'brick02', 'dev-vm', '/mnt/brick2/store-replicated'),
                    (2,'brick03', 'dev-vm', '/mnt/brick3/store-replicated'),
                    (2,'brick04', 'dev-vm', '/mnt/brick4/store-replicated'),
                    (2,'brick05', 'dev-vm', '/mnt/brick5/store-replicated'),
                    (2,'brick06', 'dev-vm', '/mnt/brick6/store-replicated'),
                    (3,'brick01', 'dev-vm', '/mnt/brick1/store'),
                    (3,'brick02', 'dev-vm', '/mnt/brick2/store'),
                    (4,'brick03', 'dev-vm', '/mnt/brick3/store'),
                    (4,'brick04', 'dev-vm', '/mnt/brick4/store'),
                    (5,'brick01', 'dev-vm', '/mnt/brick1/store-replicated'),
                    (5,'brick02', 'dev-vm', '/mnt/brick2/store-replicated'),
                    (5,'brick03', 'dev-vm', '/mnt/brick3/store-replicated'),
                    (6,'brick04', 'dev-vm', '/mnt/brick4/store-replicated'),
                    (6,'brick05', 'dev-vm', '/mnt/brick5/store-replicated'),
                    (6,'brick06', 'dev-vm', '/mnt/brick6/store-replicated'),
                    ]

        c1.executemany('INSERT INTO madbrick (volid, brickname, hostname, brickpath) VALUES (?,?,?,?)', madbrick)

        proxies = [(1, 'mad-store1', 'dev-vm', 22, 'rsync', 'rsyncclient', 'pass'),
                   (2, 'mad-replicated', 'dev-vm', 22, 'rsync', 'rsyncclient', 'pass')]

        c1.executemany('INSERT INTO proxy (proxyid, proxyname, hostname, sshport, protocol, username, passwd) VALUES (?,?,?,?,?,?,?)', proxies)

    except sqlite3.OperationalError:
        print "ERROR: importing data"
        raise
    else:
        dbconn.commit()
        print "**** Done!"
    finally:
        dbconn.close()

create_schema(sqlfile)
db_init(sqlfile)
