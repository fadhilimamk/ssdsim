#!/usr/bin/env python

# automatically break a tracefile and simulate raid
# input: tracefile
# - break that tracefile into multiple tracefiles, each for one ssd.
# - save the generated tracefile in a folder inside tracefile directory 
# - run the raid simulation using all the generated tracefiles
# - after finish, generate a single log indicating where is the statistics for every ssd in the raid simulation

import sys, math, os, datetime

IO_READ = 1
IO_WRITE = 0
OUT_TRACEFILE_DIR = 'tracefile/'
OUT_RAID_LOG_DIR = 'raw/'
RAID_SEGMENT_SIZE = 40960

# python raid <num_disk> <tracefile>
def main(argv):
    
    if len(argv) < 2:
        raise ValueError('Require the number of disk and the original tracefile')

    ndisk = int(argv[0])
    tracefilename = argv[1]

    raid_tracefiles_location = breakTracefile(tracefilename, ndisk, RAID_SEGMENT_SIZE)
    print(raid_tracefiles_location)
    runRAID(raid_tracefiles_location)

    return


# 
def breakTracefile(infile, ndisk, segment_size):
    firstline = [True] * ndisk
    outtraces = []

    crt_timestamp = datetime.datetime.now()
    timestamp_dir = crt_timestamp.strftime("%Y%m%d_%H%M%S/")
    if not os.path.exists(OUT_TRACEFILE_DIR+timestamp_dir):
        os.makedirs(OUT_TRACEFILE_DIR+timestamp_dir)
    
    for i in range (0,ndisk):
        outfile = open(OUT_TRACEFILE_DIR + timestamp_dir + infile.split("/")[-1] + "-raid5-" + str(i) + ".trace", "w")
        outtraces.append(outfile)

    # some helper function
    def writeTrace(id, trace):
        if firstline[id] is False:
            outtraces[id].write("\n")
        else:
            firstline[id] = False
        outtraces[id].write(trace)

    blk_size = 1024 # or sector size in hdd (in bytes)
    blk_per_segment = segment_size / blk_size
    blk_per_stripe = blk_per_segment * (ndisk - 1) # --- modf_1 --- ndisk -> (ndisk-1) (Sep.17 17:19)

    intrace = open(infile, "r")
    for line in intrace:
        token = line.split()
        time = int(token[0])
        devno = token[1]
        blkno = int(token[2])
        blkcount = int(token[3])
        operation = int(token[4])

        # calculating new starting blkno
        target_stripe_id = blkno / (blk_per_segment * (ndisk-1))
        blk_stripe_offset = (blkno + (blk_per_segment*target_stripe_id)) % blk_per_stripe
        parity_disk_id = target_stripe_id % ndisk
        target_disk_id = blk_stripe_offset / blk_per_segment
        if parity_disk_id <= target_disk_id: # right shift 1 disk to jump over parity disk
            target_disk_id = target_disk_id + 1
        new_blkno = (target_stripe_id*blk_per_segment) + (blk_stripe_offset%blk_per_segment)

        # iterate blkcount
        current_disk_id = target_disk_id
        current_stripe_id = target_stripe_id
        current_blkno = new_blkno
        current_blkcount = blkcount
        next_segment_blk = (current_stripe_id+1)*blk_per_segment

        max_blkcount_segment = 0
        min_blkno_segment = current_blkno

        while blkcount > 0:
            current_blkcount = blkcount # --- add_1 --- (Sep.18 14:24)

            if current_blkcount + current_blkno > next_segment_blk:
                current_blkcount = next_segment_blk-current_blkno

            if operation == 0:
                writeTrace(current_disk_id, "{} {} {} {} {}".format(time, devno, current_blkno, current_blkcount, 1))
            writeTrace(current_disk_id, "{} {} {} {} {}".format(time, devno, current_blkno, current_blkcount, operation))

            max_blkcount_segment = 0 # --- add_3 --- (Sep.18 20:05)
            if max_blkcount_segment < current_blkcount: 
                max_blkcount_segment = current_blkcount

            blkcount = blkcount - current_blkcount

            # write parity for last stripe
            if operation == 0 and blkcount <= 0 :
                writeTrace(current_stripe_id%ndisk, "{} {} {} {} {}".format(time, devno, min_blkno_segment, max_blkcount_segment, 1))
                writeTrace(current_stripe_id%ndisk, "{} {} {} {} {}".format(time, devno, min_blkno_segment, max_blkcount_segment, operation))
                break

            # move to next segment and skip parity segment
            while True:
                
                current_disk_id = current_disk_id + 1 # move to next disk

                if current_disk_id == ndisk: # current disk is rightmost disk of current stripe, so move to next stripe

                    if operation == 0: # write parity before change to next stripe (only for write operation)
                        writeTrace(current_stripe_id%ndisk, "{} {} {} {} {}".format(time, devno, min_blkno_segment, max_blkcount_segment, 1))
                        writeTrace(current_stripe_id%ndisk, "{} {} {} {} {}".format(time, devno, min_blkno_segment, max_blkcount_segment, operation))

                    current_disk_id = 0 # start over from disk_0
                    current_stripe_id = current_stripe_id + 1 # move to next stripe

                if current_disk_id != current_stripe_id%ndisk: # current disk is not parity disk
                    current_blkno = current_stripe_id * blk_per_segment # head of blkno in a segment
                    min_blkno_segment = current_blkno
                    max_blkcount_segment = blk_per_segment # --- add_2 --- (Sep.18 16:38)
                    break

            next_segment_blk = (current_stripe_id+1)*blk_per_segment

    return outtraces

def runRAID(tracefiles_loc):
    # ./ssd tracefile_loc[i]

    # generate log
    return

if __name__ == "__main__":
    main(sys.argv[1:])

