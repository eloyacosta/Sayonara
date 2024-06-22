#!/bin/bash
# SAYONARA AGENT 1.1b
# 10/2016
# Eloy Acosta

AGENT_HOME="$HOME/sayonara"
AGENT_CONF=${AGENT_HOME}/sayonara_agent.conf
source ${AGENT_CONF}

mkdir -p ${STATUSDIR}

rsync_proc() {
        SRCBASEPATH=$1
        DEST_SERVICE=$2
        VOL=$3
        RSYNCSERVER=$4
        RSYNC_USER=$5
        RSYNC_PASS=$6
        LOCK_FILE=${STATUSDIR}/$$.lock
        FIN_FILE=${STATUSDIR}/$$.done
        RSYNC_LOG_FILE=${STATUSDIR}/$$.rsync.log
        # We use the .lock and the .done file to control on the process execution

        case ${DEST_SERVICE} in
            "CV")
                RSYNC_OPTS=${CV_RSYNC_OPTS}
                ;;
            "CP" | "CP1" | "CP2" | "CP3")
                RSYNC_OPTS=${CP_RSYNC_OPTS}
                ;;
            *)
                RSYNC_OPTS=""
                ;;
        esac

        touch ${LOCK_FILE} && \
        RSYNC_PASSWORD=${RSYNC_PASS} \
        rsync ${RSYNC_OPTS} ${SRCBASEPATH} rsync://${RSYNC_USER}@${RSYNCSERVER}/${RSYNCEXPORT}/${VOL} > ${RSYNC_LOG_FILE} 2>&1 && \
        mv ${LOCK_FILE} ${FIN_FILE}
}


check_process() {

        # TODO: If the PPID (the agent itself) is killed the children keeps running. Have to improve this.
        OSPID=$1
        LOCK_FILE=$STATUSDIR/$OSPID.lock
        FIN_FILE=$STATUSDIR/$OSPID.done

        # There are 4 status codes: 0 = running, 1 = finished, 2 = killed, 3 = inconsistent
        # If there's a lock file the process may be running or killed
        if [ -f "$LOCK_FILE" ]; then
            [ -e /proc/${OSPID} ] && echo "0:$OSPID" || echo "2:$OSPID"
        # Otherwise, it can be finished or inconsistent
        else
            [ -f "$FIN_FILE" ] && echo "1:$OSPID" || echo "3:$OSPID"
        fi
}


check_mount() {
        VOL=$1
        # WARN: This is case sensitive
        mountpoint -q ${MOUNTBASEDIR}/${VOL} && \
        #Return 0 and the space available (in bytes)
        echo "0:"$(df -T ${MOUNTBASEDIR}/${VOL} | grep -i ${MOUNTBASEDIR}/${VOL} | awk {'print $4'}) || \
        #This is not a mount point
        echo "1:-1"
        }


mount_vol() {
        PROTOCOL=$1
        SERVERHOST=$2
        VOL=$3
        VOL_USERNAME=$4
        VOL_PASSWD=$5
        mkdir -p ${MOUNTBASEDIR}/$3 && \
        mount -t ${PROTOCOL} //${SERVERHOST}/${VOL} ${MOUNTBASEDIR}/${VOL}/ -ousername=${VOL_USERNAME},domain=${DOMAIN} > /dev/null 2>&1 &&
        echo "0:"$(df -T ${MOUNTBASEDIR}/${VOL} | grep -i ${MOUNTBASEDIR}/${VOL} | awk {'print $4'}) || \
        echo "1:-1"
}


SUBCMD=$1

case ${SUBCMD} in
    "run")
        rsync_proc $2 $3 $4 $5 $6 $7
        ;;

    "check")
        check_process $2
        ;;

    "kill")
        OSPID=$2

        for i in $(ps h -o pid --ppid=${OSPID}); do
            kill -9 ${i};
        done
        #sleep 1
        ;;

    "checkmount")
        check_mount $2
        ;;

    "mount")
        mount_vol $2 $3 $4 $5 $6
        ;;

    *)
        echo -1:-1
    ;;

esac


