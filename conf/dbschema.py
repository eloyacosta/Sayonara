import sqlite3

def create_schema(sqlfile):

    dbconn = sqlite3.connect(sqlfile)
    c1 = dbconn.cursor()

    print('*** Creating Database Schema...')

    try:
        c1.executescript("""
            CREATE TABLE job(
                jobid INTEGER PRIMARY KEY AUTOINCREMENT,
                stimestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                ftimestamp TIMESTAMP,
                sourcevol TEXT,
                volid INTEGER,
                labpath TEXT,
                dest TEXT,
                destservice TEXT,
                proxyname TEXT,
                status INTEGER,
                pdegree INTEGER,
                FOREIGN KEY(volid) REFERENCES madvol(volid)
            );

            CREATE TABLE process(
                processid INTEGER PRIMARY KEY AUTOINCREMENT,
                stimestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                ftimestamp TIMESTAMP,
                jobid INTEGER,
                ospid INTEGER,
                user TEXT,
                hostname TEXT,
                port INTEGER,
                brickname TEXT,
                brickpath TEXT,
                FOREIGN KEY(jobid) REFERENCES job(jobid)
            );

            CREATE TABLE madvol(
                volid INTEGER PRIMARY KEY,
                volname TEXT,
                voltype TEXT
            );

            CREATE TABLE madbrick(
                brickid INTEGER PRIMARY KEY AUTOINCREMENT,
                volid INTEGER,
                brickname TEXT,
                hostname TEXT,
                brickpath TEXT,
                FOREIGN KEY(volid) REFERENCES madvol(volid)
            );

            CREATE TABLE proxy(
                proxyid INTEGER PRIMARY KEY AUTOINCREMENT,
                proxyname TEXT UNIQUE,
                hostname TEXT,
                sshport INTEGER,
                protocol TEXT,
                username TEXT,
                passwd TEXT
            );
            """)

    except sqlite3.OperationalError:
        print "Error creating the schema. It may exists already"
        raise
    else:
        # Populate db with config data

        dbconn.commit()
        print "**** Schema successfully created"
    finally:
        dbconn.close()
