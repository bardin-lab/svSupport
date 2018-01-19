import sys, os, re
import pysam
from optparse import OptionParser

out_dir = '../out'
debug = 0

def bp1_supporting_reads(bamFile, chrom, bp1, bp2, slop):
    samfile = pysam.Samfile(bamFile, "rb")
    start=bp1-slop
    bp1_reads = []
    out_file = os.path.join(out_dir, "bp1_sv_reads" + ".bam")
    bp1_sv_reads = pysam.AlignmentFile(out_file, "wb", template=samfile)
    count = 0
    for read in samfile.fetch(chrom, start, bp1):
        read_end_pos = read.pos + read.alen
        mate_end_pos = read.mpos + read.alen

        if not read.is_proper_pair and not read.is_reverse and read.mpos > bp2:
            if debug:
                print("* bp1 disc_read    : %s %s [rs:e: %s-%s, ms:e: %s-%s]") % (read.qname, read.seq, read.pos, read_end_pos, read.mpos, mate_end_pos)
            bp1_sv_reads.write(read)
            bp1_reads.append(read.qname)
            count += 1

        if read_end_pos == bp1:
            if debug:
                print("* bp1 clipped_read : %s %s [r0: %s, rend: %s]") % (read.qname, read.seq, read.pos, read_end_pos)
            bp1_sv_reads.write(read)
            bp1_reads.append(read.qname)
            count += 1

    bp1_sv_reads.close()
    pysam.index(out_file)

    return(bp1_reads, count)


def bp2_supporting_reads(bamFile, chrom, bp1, bp2, slop):
    samfile = pysam.Samfile(bamFile, "rb")
    end=bp2+slop
    bp2_reads = []
    out_file = os.path.join(out_dir, "bp2_sv_reads" + ".bam")
    bp2_sv_reads = pysam.AlignmentFile(out_file, "wb", template=samfile)

    count = 0

    for read in samfile.fetch(chrom, bp2, end):
        read_end_pos = read.pos + read.alen
        mate_end_pos = read.mpos + read.alen

        if not read.is_proper_pair and read.is_reverse and mate_end_pos < bp1:
            if debug:
                print("* bp2 disc_read    : %s %s [rs:e: %s-%s, ms:e: %s-%s]") % (read.qname, read.seq, read.pos, read_end_pos, read.mpos, mate_end_pos)
            bp2_sv_reads.write(read)
            bp2_reads.append(read.qname)
            count += 1

        if read.pos +1 == bp2:
            if debug:
                print("* bp2 clipped_read : %s %s [r0: %s, rend: %s]") % (read.qname, read.seq, read.pos, read_end_pos)
            bp2_reads.append(read.qname)
            bp2_sv_reads.write(read)
            count += 1

    bp2_sv_reads.close()
    pysam.index(out_file)

    return(bp2_reads, count)


def bp_1_opposing_reads(bamFile, chrom, bp1, bp2, slop):
    samfile = pysam.Samfile(bamFile, "rb")
    start=bp1-slop
    bp1_reads = []
    out_file = os.path.join(out_dir, "bp1_opposing_reads" + ".bam")
    bp1_opposing_reads = pysam.AlignmentFile(out_file, "wb", template=samfile)
    count = 0
    for read in samfile.fetch(chrom, start, bp1):
        read_end_pos = read.pos + read.alen
        mate_end_pos = read.mpos + read.alen

        if read.is_proper_pair and not read.is_reverse and read.mpos > bp1 and not read.is_supplementary:
            if debug:
                print("* bp1 opposing read    : %s %s [rs:e: %s-%s, ms:e: %s-%s]") % (read.qname, read.seq, read.pos, read_end_pos, read.mpos, mate_end_pos)
            bp1_opposing_reads.write(read)
            bp1_reads.append(read.qname)
            count += 1

        elif read.pos < bp1 and read_end_pos > bp1:
            if debug:
                print("* bp1 spanning read    : %s %s [rs:e: %s-%s, ms:e: %s-%s]") % (read.qname, read.seq, read.pos, read_end_pos, read.mpos, mate_end_pos)
            bp1_opposing_reads.write(read)
            bp1_reads.append(read.qname)
            count += 1

    bp1_opposing_reads.close()
    pysam.index(out_file)

    return(bp1_reads, count)


def bp_2_opposing_reads(bamFile, chrom, bp1, bp2, slop):
    samfile = pysam.Samfile(bamFile, "rb")
    end=bp2+slop
    bp2_reads = []
    out_file = os.path.join(out_dir, "bp2_opposing_reads" + ".bam")
    bp2_opposing_reads = pysam.AlignmentFile(out_file, "wb", template=samfile)
    count = 0
    for read in samfile.fetch(chrom, bp2, end):
        read_end_pos = read.pos + read.alen
        mate_end_pos = read.mpos + read.alen

        if read.is_proper_pair and read.is_reverse and read.mpos < bp2 and not read.is_supplementary and read.mpos +1 != bp2:
            if debug:
                print("* bp2 opposing read    : %s %s [rs:e: %s-%s, ms:e: %s-%s]") % (read.qname, read.seq, read.pos, read_end_pos, read.mpos, mate_end_pos)
            bp2_opposing_reads.write(read)
            bp2_reads.append(read.qname)
            count += 1

        elif read.pos < bp1 and read_end_pos > bp1:
            if debug:
                print("* bp2 spanning read    : %s %s [rs:e: %s-%s, ms:e: %s-%s]") % (read.qname, read.seq, read.pos, read_end_pos, read.mpos, mate_end_pos)
            bp2_opposing_reads.write(read)
            bp2_reads.append(read.qname)
            count += 1

    bp2_opposing_reads.close()
    pysam.index(out_file)

    return(bp2_reads, count)

def merge_bams(out_file, bams):
    # out_file = os.path.join(out_dir, out_file)
    in_files = ', '.join(bams)
    print("Merging bam files '%s' into '%s'") % (in_files, out_file)
    merge_parameters = ['-f', out_file] + bams
    pysam.merge(*merge_parameters)
    pysam.index(out_file)


def findSupport(bam_in, chrom, bp1, bp2, slop):
    bp1_sv_reads, bp1_read_count = bp1_supporting_reads(bam_in, chrom, bp1, bp2, slop)
    bp2_sv_reads, bp2_read_count = bp2_supporting_reads(bam_in, chrom, bp1, bp2, slop)

    bam1 = os.path.join(out_dir, "bp1_sv_reads" + ".bam")
    bam2 = os.path.join(out_dir, "bp2_sv_reads" + ".bam")
    out = os.path.join(out_dir, "sv_support" + ".bam")

    total_support = bp1_read_count + bp2_read_count

    print("Found %s reads in support of variant" % total_support)
    to_merge = [bam1, bam2]
    merge_bams(out, to_merge)
    return(bp1_sv_reads, bp1_read_count, bp2_sv_reads, bp2_read_count)


def findOpposing(bam_in, chrom, bp1, bp2, slop):
    bp1_opposing_reads, bp1_opposing_read_count = bp_1_opposing_reads(bam_in, chrom, bp1, bp2, slop)
    bp2_opposing_reads, bp2_opposing_read_count = bp_2_opposing_reads(bam_in, chrom, bp1, bp2, slop)

    total_oppose = bp1_opposing_read_count + bp2_opposing_read_count
    print("Found %s reads opposing variant" % total_oppose)

    bam1 = os.path.join(out_dir, "bp1_opposing_reads" + ".bam")
    bam2 = os.path.join(out_dir, "bp2_opposing_reads" + ".bam")
    out = os.path.join(out_dir, "sv_oppose" + ".bam")
    to_merge = [bam1, bam2]
    merge_bams(out, to_merge)

    return(bp1_opposing_reads, bp1_opposing_read_count, bp2_opposing_reads, bp2_opposing_read_count)


def calculate_allele_freq(bp1_read_count, bp2_read_count, bp1_opposing_read_count, bp2_opposing_read_count):
    total_support =  bp1_read_count + bp2_read_count
    total_oppose = bp1_opposing_read_count + bp2_opposing_read_count

    allele_frequency = float(total_support)/(float(total_support)+float(total_oppose))
    # QA/(QR+QA)
    print("Allele frequency: %s" % allele_frequency)
    return(allele_frequency)


def make_dirs(bam_file, out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

def print_options(bam_in, chrom, bp1, bp2, slop, debug, out_dir):
    options = ['Bam file', 'Chrom', 'bp1', 'bp2', 'slop', 'debug', 'Out dir']
    given = [bam_in, chrom, bp1, bp2, slop, debug, out_dir]
    print("----")
    for index, (value1, value2) in enumerate(zip(options, given)):
         print("%s: %s") % (value1, value2)
    print("----")


def main():
    parser = OptionParser()

    parser.add_option("-i", \
                      "--in_file", \
                      dest="in_file",
                      action="store",
                      help="A sorted .bam file containing the reads " + \
                           "supporting the structural variant calls", \
                           metavar="FILE")

    parser.add_option("-s", \
                      "--slop", \
                      dest="slop",
                      # default=500,
                      action="store",
                      help="Distance from breakpoint to look for reads" + \
                           "Default: 500")

    parser.add_option("-l", \
                      "--loci", \
                      dest="region",
                      action="store",
                      help="The chromosome and breakpoints for a " + \
                           "structural variant in the format: " + \
                           "'chrom:bp_1-bp_2'")

    parser.add_option("-o", \
                      "--out_dir", \
                      dest="out_dir",
                      action="store",
                      help="Directory to write output to")


    parser.add_option("-d", \
                      "--debug", \
                      dest="debug",
                      action="store_true",
                      help="Run in debug mode")

    parser.set_defaults(slop=500, out_dir='../out', debug=0)

    options, args = parser.parse_args()

    global out_dir
    global debug


    if options.in_file is None:
        parser.print_help()
        print
    else:
        try:
            bam_in = options.in_file
            region = options.region
            slop   = options.slop
            out_dir = options.out_dir
            debug = options.debug

            chrom, bp1, bp2 = re.split(':|-', region)
            bp1 = int(bp1)
            bp2 = int(bp2)
            slop = int(slop)

            if debug:
                print_options(bam_in, chrom, bp1, bp2, slop, debug, out_dir)

            make_dirs(bam_in, out_dir)
            bp1_sv_reads, bp1_read_count, bp2_sv_reads, bp2_read_count = findSupport(bam_in, chrom, bp1, bp2, slop)
            bp1_opposing_reads, bp1_opposing_read_count, bp2_opposing_reads, bp2_opposing_read_count = findOpposing(bam_in, chrom, bp1, bp2, slop)

            allele_frequency = calculate_allele_freq(bp1_read_count, bp2_read_count, bp1_opposing_read_count, bp2_opposing_read_count)

        except IOError as err:
            sys.stderr.write("IOError " + str(err) + "\n");
            return

if __name__ == "__main__":
    sys.exit(main())