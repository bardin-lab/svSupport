import pysam
from collections import defaultdict
import re, os


def get_reads(bp_regions, bp_number, chrom, bp, chrom2, bp2, options, seen_reads, chroms, supporting, opposing):
    """Get reads supporting a breakpoint and write both discordant and clipped supporting reads.
       Count the evidence supporting different types of breakpoint arrangements and return the one
       with most support:

       f_bp : ---->[x]=====
       bp_f : =====[x]---->
       r_bp : <----[x]=====
       bp_r : =====[x]<----

       """
    svID = '_'.join(map(str, [chrom, bp]))

    clipped_out = os.path.join(options.out_dir, bp_number + "_" + svID + "_clipped_reads" + ".bam")
    disc_out = os.path.join(options.out_dir, bp_number + "_" + svID + "_disc_reads" + ".bam")
    opposing_reads = os.path.join(options.out_dir, bp_number + "_" + svID + "_opposing" + ".bam")

    samfile = pysam.Samfile(bp_regions, "rb")
    printmate = defaultdict(int)

    bp_sig = defaultdict(int)

    if options.debug: print(" * Looking for reads supporting %s" % bp_number)

    with pysam.AlignmentFile(clipped_out, "wb", template=samfile) as bpReads, pysam.AlignmentFile(disc_out, "wb", template=samfile) as discReads, pysam.AlignmentFile(opposing_reads, "wb", template=samfile) as op_reads:
        split_reads = 0

        start = bp - 500
        stop = bp + 500

        alien_split = 0
        alien_paired = 0
        te_tagged = defaultdict(int)
        alien_integrant = defaultdict(int)

        for read in samfile.fetch(chrom, start, stop):

            if not read.infer_read_length():
                """This is a problem - and will skip over reads with no mapped mate (which also have no cigar)"""
                continue

            if read.is_reverse:
                direction = 'r'
            else:
                direction = 'f'

            read, bp_sig, split_reads, bpID = getClipped(read, bp, direction, bp_number, bp_sig, split_reads, options)

            if bpID:
                bpReads.write(read)
                supporting.append(read.query_name)

            read, bp_sig, bpID, seen_reads = disc_reads(read, bp2, bp_sig, bp_number, direction, options, seen_reads)

            if bpID:
                discReads.write(read)
                supporting.append(read.query_name)

            if not bpID and not read.query_name in supporting:
                read, bpID, printmate = getOpposing(read, bp, bp_number, printmate)
                if bpID:
                    op_reads.write(read)
                    opposing.append(read.query_name)

            if options.chromfile:
                alien_integrant = getAlienDNA(bpID, read, alien_integrant, chroms, bp_number, direction, options)
            te_tagged = getTaggedReads(bpID, read, te_tagged, bp_number, bp, direction, options)

    pysam.index(clipped_out)
    pysam.index(disc_out)
    pysam.index(opposing_reads)

    return clipped_out, disc_out, opposing_reads, alien_integrant, te_tagged, bp_sig, seen_reads, supporting, opposing


def getOpposing(read, bp, bp_number, printmate):
    bpID = None

    if printmate[read.query_name] >= 1:
        bpID = '_'.join([str(bp_number), 'opposing'])
        tag = ' '.join(['opposing', 'pair'])

    elif read.reference_start < bp and read.reference_end > bp:
        bpID = '_'.join([str(bp_number), 'opposing'])
        tag = ' '.join(['opposing', 'spanning'])

    elif read.reference_end < bp and read.next_reference_start > bp:
        bpID = '_'.join([str(bp_number), 'opposing'])
        tag = ' '.join(['opposing', 'pair'])
        printmate[read.query_name] += 1

    if bpID:
        tagRead(read, tag)

    return read, bpID, printmate


def disc_reads(read, bp2, bp_sig, bp_number, direction, options, seen_reads):
    """Return true if read is both discordant (not read.is_proper_pair)
       and not contained in f/r reads dict. This prevents the same read being counted
       twice in regions that overlap"""

    bpID = None

    read_key = '_'.join([read.query_name, str(read.reference_start)])
    seen_reads[read_key] += 1

    if read.is_duplicate or seen_reads[read_key] > 1:
        return read, bp_sig, None, seen_reads

    if not read.is_proper_pair and (abs(read.next_reference_start - bp2) <= 350):
        if direction == 'r':
            bpID = '_'.join([bp_number, 'r'])
            if options.debug: print("<---- discordant read supports breakpoints %s: %s") % (bp_number, read.query_name)
        else:
            bpID = '_'.join(['r', bp_number])
            if options.debug: print("----> discordant read supports breakpoints %s: %s") % (bp_number, read.query_name)

    if bpID:
        tag = ' '.join(['discordant', direction, 'read'])
        tagRead(read, tag)
        bp_sig[bpID] += 1

    return read, bp_sig, bpID, seen_reads


def getAlienDNA(bpID, read, alien_integrant, chroms, bp_number, direction, options):
    if bpID and read.is_supplementary:
        try:
            sa_chrom = read.get_tag('SA').split(',')[0]
            if sa_chrom not in chroms:
                alien_integrant[sa_chrom] += 1
                if options.debug: print "Clipped reads partially aligns to non-reference chromosome: %s (%s)" % (sa_chrom, read.query_name)
        except:
            pass

    elif read.next_reference_name not in chroms:
        alienchrom = str(read.next_reference_name)
        if bp_number == 'bp1' and direction == 'f':
            if options.debug: print "forward read has mate mapped to non-reference chromosome: %s (%s)" % (read.next_reference_name, read.query_name)
            alien_integrant[alienchrom] += 1
        elif bp_number == 'bp2' and direction == 'r':
            if options.debug: print "reverse read has mate mapped to non-reference chromosome: %s (%s)" % (read.next_reference_name, read.query_name)
            alien_integrant[alienchrom] += 1

    return alien_integrant


def getTaggedReads(bpID, read, te_tagged, bp_number, bp, direction, options):
    if bpID and read.is_supplementary:
        try:
            sa_te = read.get_tag('AD').split(',')[0]
            sa_te = '_'.join(sa_te.split('_')[1:])
            if options.debug: print "clipped:", sa_te, read.query_name
            te_tagged[sa_te] += 1
        except KeyError:
            pass
    try:
        te = read.get_tag('BR').split(',')[0]
        te = '_'.join(te.split('_')[1:])

        if direction == 'f' and read.reference_start < bp:
        # if bp_number == 'bp1' and direction == 'f':
            if options.debug: print "foward read has mate in te:", te, read.query_name
            te_tagged[te] += 1
        elif direction == 'r' and read.reference_end > bp:
            if options.debug: print "reverse read has mate in te:", te, read.query_name
            te_tagged[te] += 1
    except KeyError:
        pass

    return te_tagged


def getClipped(read, bp, direction, bp_number, bp_sig, split_reads, options):
    """If reads are clipped at the breakpoint, classify them based on their mapping signature:
       f_bp : ---->[x]=====
       bp_f : =====[x]---->
       r_bp : <----[x]=====
       bp_r : =====[x]<----
       """

    bpID = None
    # if clipped
    if re.findall(r'(\d+)[S|H]', read.cigarstring):

        # if right-clipped
        if bp == read.reference_end:
            bpID = rightClipped(read, direction, bp_number, options)
        # if read is left-clipped
        elif bp == read.reference_start + 1:
            bpID = leftClipped(read, direction, bp_number, options)

        if bpID:
            tag = ' '.join(['clipped', direction, 'read'])
            tagRead(read, tag)
            bp_sig[bpID] += 1
            split_reads += 1

    return read, bp_sig, split_reads, bpID


def rightClipped(read, direction, bp_number, options):
    """Looks for reads that are clipped to the right of breakpoint"""
    if re.findall(r".*?M(\d+)[S|H]", read.cigarstring):
        if options.debug:
            if direction == 'f':
                print("---> read clipped to right: %s --[-> %s") % (read.cigarstring, read.query_name)
            else:
                print("<--- read clipped to right: %s <--[- %s") % (read.cigarstring, read.query_name)
        bpID = '_'.join(['r', bp_number])
        return bpID


def leftClipped(read, direction, bp_number, options):
    """Looks for reads that are clipped to the left of breakpoint"""
    if re.findall(r'(\d+)[S|H].*?M', read.cigarstring):
        if options.debug:
            if direction == 'f':
                print("---> read clipped to left: %s -]--> %s") % (read.cigarstring, read.query_name)
            else:
                print("<--- read clipped to left: %s <-]-- %s") % (read.cigarstring, read.query_name)
        bpID = '_'.join([bp_number, 'r'])
        return bpID


def tagRead(read, tag):
    """Tag read with custom tag 'SV' - indicating its involvement in SV"""
    read.set_tag('SV', tag, value_type='Z')
    return read
