#!/usr/bin/env python
from __future__ import division
import os, re
import pysam
import sys
sys.dont_write_bytecode = True
from collections import defaultdict
from optparse import OptionParser
from deletions import Deletions
from inversions import Inversions
from find_reads import FindReads
from merge_bams import merge_bams


def calculate_allele_freq(total_support, total_oppose, tumour_purity):
    print("Tumour purity set to %s" % tumour_purity)
    allele_frequency = float( total_support/(total_support+total_oppose) )
    if tumour_purity == 1:
        adj_allele_frequency = allele_frequency
    else:
        adj_allele_frequency = float( total_support/( total_support + (total_oppose**tumour_purity) ) )

    allele_frequency = "{:.2f}".format(allele_frequency)
    adj_allele_frequency = "{:.2f}".format(adj_allele_frequency)
    print("Adjusted allele frequency from %s to %s") % (allele_frequency, adj_allele_frequency)

    return(allele_frequency)


def make_dirs(bam_file, out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)


def print_options(bam_in, ratio_file, chrom, bp1, bp2, slop, find_bps, debug, test, out_dir):
    options = ['Bam file', 'Read depth ratio file', 'Chrom', 'bp1', 'bp2', 'slop', 'hone_bps', 'debug', 'test', 'Out dir']
    args = [bam_in, ratio_file, chrom, bp1, bp2, slop, find_bps, debug, test, out_dir]
    print("Running with options:")
    print("--------")
    for index, (value1, value2) in enumerate(zip(options, args)):
         print("o %s: %s") % (value1, value2)
    print("--------")
    print("python svSupport.py -i %s -l %s:%s-%s -s %s -f %s -t %s -d %d -o %s") % (bam_in, chrom, bp1, bp2, slop, find_bps, test, debug, out_dir )
    print("--------")


def F_bp(read, bp):
    if not read.is_proper_pair and (not read.is_reverse and read.reference_start < bp):
        return True

def bp_R(read, bp):
    if not read.is_proper_pair and (read.is_reverse and read.reference_start + read.reference_length > bp):
        return True

def bp_F(read, bp):
    if not read.is_proper_pair and (not read.is_reverse and read.reference_start + read.reference_length > bp):
        return True

def guess_type(bamFile, chrom, bp, bp_number, out_dir, debug):
    samfile = pysam.Samfile(bamFile, "rb")
    start = bp - 300
    stop = bp + 300

    # print("Searching for SV type in region: %s:%s-%s") % (chrom, start, stop)

    sv_reads = defaultdict(int)

    count = 0
    out_file = os.path.join(out_dir, bp_number + "_classifying_reads" + ".bam")

    with pysam.AlignmentFile(out_file, "wb", template=samfile) as bpReads:

        for read in samfile.fetch(chrom, start, stop):
            read_end_pos = read.reference_start + read.reference_length
            mate_end_pos = read.next_reference_start + read.reference_length

            if bp_number == 'bp1':
                if F_bp(read, bp):
                    sv_reads['F_bp1'] += 1
                    bpReads.write(read)
                elif bp_R(read, bp):
                    sv_reads['bp1_R'] += 1
                    bpReads.write(read)

            elif bp_number == 'bp2':
                if bp_R(read, bp):
                    sv_reads['bp2_R'] += 1
                    bpReads.write(read)
                elif F_bp(read, bp):
                    sv_reads['F_bp2'] += 1
                    bpReads.write(read)

    pysam.index(out_file)

    sv_reads['NA'] = 0
    maxValKey = max(sv_reads, key=sv_reads.get)

    return(sv_reads, maxValKey)


def get_depth(chrom, bp1, bp2, ratio_file):

    count = 1
    average_ratio = 0

    with open(ratio_file, 'r') as depth_ratios:
        for l in depth_ratios:
            parts = l.rstrip().split('\t')
            if parts[0] == 'Chromosome':
                continue

            pos = int(parts[1])
            ratio = float(parts[2])

            if parts[0] == chrom and pos >= bp1 and pos <= bp2:
                average_ratio = ratio/count
                count += 1

                print(parts[0], parts[1], parts[2])

        allele_freq = (1-average_ratio)
        print("Allele frequency derived from read depth ratio = %s") % (allele_freq)
        return(allele_freq)


def hone_bps(bam_in, chrom, bp, bp_class):
    samfile = pysam.Samfile(bam_in, "rb")
    start = bp - 5
    stop = bp + 5

    bp_reads = {}
    for i in range(start, stop):
        count = 0

        for read in samfile.fetch(chrom, i-1, i+1):
            read_end_pos   = read.reference_start + read.alen
            read_start_pos = read.reference_start

            if bp_class == 'F_bp1' or bp_class == 'F_bp2':
                if read_end_pos == i:
                    count+=1
                    bp_reads[i] = count

            elif bp_class == 'bp2_R' or bp_class == 'bp1_R':
                if read.reference_start +1 == i:
                    count+=1
                    bp_reads[i] = count

    maxValKey = max(bp_reads, key=bp_reads.get)
    read_count = bp_reads[maxValKey]

    return(maxValKey, read_count)


def get_args():
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
                    action="store",
                    type="int",
                    help="Distance from breakpoint to look for reads " + \
                         "[Default: 500]")

    parser.add_option("-p", \
                     "--purity", \
                     dest="purity",
                     action="store",
                     help="Tumour purity e.g. 0.75 " + \
                          "[Default: True]")

    parser.add_option("-f", \
                     "--find_bps", \
                     dest="find_bps",
                     action="store_true",
                     help="Look for bps if position not exact " + \
                          "[Default: False]")

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
                    help="Directory to write output to " + \
                         "[Default: '../out']")


    parser.add_option("-d", \
                    "--debug", \
                    dest="debug",
                    action="store_true",
                    help="Run in debug mode "  + \
                         "[Default: False]")

    parser.add_option("-t", \
                    "--test", \
                    dest="test",
                    action="store_true",
                    help="Run on test data")


    parser.add_option("-r", \
                    "--ratio", \
                    dest="ratio_file",
                    action="store",
                    help="Read depth ratio file " + \
                         "Must be fmtd: chromosome\tstart\tratio")

    parser.set_defaults(slop=500, out_dir='../out', debug=False, test=False, purity=1, find_bps=False)
    options, args = parser.parse_args()

    if (options.in_file is None or options.region is None) and options.test is False:
      parser.print_help()
      print

    return(options, args)


def main():
    options, args = get_args()

    global out_dir
    global debug

    if options.test is True:
        print
        print("Running in test mode...")
        print

        options.region = '3L:9892365-9894889'
        options.out_dir = '../test_out'
        options.in_file = '../data/test.bam'
        options.debug = True

    if options.ratio_file is not None:
        ratio_file = options.ratio_file
    else:
        ratio_file = 'NA'

    if options.in_file is not None and options.region is not None:
        try:
            bam_in   = options.in_file
            region   = options.region
            slop     = options.slop
            out_dir  = options.out_dir
            debug    = options.debug
            purity   = float(options.purity)
            find_bps = options.find_bps
            test     = options.test

            chrom, bp1, bp2 = re.split(':|-', region)
            bp1 = int(bp1)
            bp2 = int(bp2)
            slop = int(slop)

            if debug:
                print_options(bam_in, ratio_file, chrom, bp1, bp2, slop, find_bps, debug, test, out_dir)

            #-------------------
            # Adjust breakpoints
            #-------------------

            find_type = 1;

            if find_type:
                bp1_reads, bp1_best_guess = guess_type(bam_in, chrom, bp1, 'bp1', out_dir, debug)
                bp1_best_guess = max(bp1_reads, key=bp1_reads.get)
                bp2_reads, bp2_best_guess = guess_type(bam_in, chrom, bp2, 'bp2', out_dir, debug)
                bp2_best_guess = max(bp2_reads, key=bp2_reads.get)

                if bp1_best_guess == 'F_bp1' and bp2_best_guess == 'bp2_R':
                    print("Deletion")
                    sv_type = 'DEL'
                elif bp1_best_guess == 'bp1_R' and bp2_best_guess == 'bp2_R':
                    print("Inversion")
                    sv_type = 'INV'
                elif bp1_best_guess == 'F_bp1' and bp2_best_guess == 'F_bp2':
                    print("Inversion")
                    sv_type = 'INV'
                elif bp1_best_guess == 'bp1_R' and bp2_best_guess == 'F_bp2':
                    print("Duplication")
                    sv_type = 'DUP'
                elif bp1_best_guess == 'NA' and bp2_best_guess == 'NA':
                    print("* Can't classify SV - will continue assuming a deletion as default")
                    sv_type = 'DEL'
                else:
                    print("-> Don't know")
                    sv_type = ''

            else:
                bp1_best_guess, bp2_best_guess = 'F_bp1', 'bp2_R'

            print(bp1_best_guess, bp2_best_guess)


            if ratio_file != 'NA':
                allele_frequency = get_depth(chrom, bp1, bp2, ratio_file)
                print("%s\t%s\t%s\t%s") % (chrom, bp1, bp2, allele_frequency)
                sys.exit()

            if find_bps:
                bp1, bp1_count = hone_bps(bam_in, chrom, bp1, bp1_best_guess)
                bp2, bp2_count = hone_bps(bam_in, chrom, bp2, bp2_best_guess)

                print("Bp1 adjusted to: %s [%s split reads found]") % (bp1, bp1_count)
                print("Bp2 adjusted to: %s [%s split reads found]") % (bp2, bp2_count)

            make_dirs(bam_in, out_dir)
            supporting_reads = []


            reads = FindReads(bam_in, chrom, bp1, bp2, slop, out_dir, debug, bp1_best_guess, bp2_best_guess)
            bp1_supporting_reads, bp1_support_count, bp1_support_bam, bp1_opposing_reads, bp1_oppose_count, bp1_oppose_bam = reads.bp1_reads()
            bp2_supporting_reads, bp2_support_count, bp2_support_bam, bp2_opposing_reads, bp2_oppose_count, bp2_oppose_bam = reads.bp2_reads()

            support_out = os.path.join(out_dir, "sv_support" + ".bam")
            oppose_out = os.path.join(out_dir, "sv_oppose" + ".bam")

            merge_bams(support_out, [bp1_support_bam, bp2_support_bam])
            merge_bams(oppose_out, [bp1_oppose_bam, bp2_oppose_bam])

            all_su_reads = bp1_supporting_reads + bp2_supporting_reads
            total_support = len(set(all_su_reads))

            all_op_reads = bp1_opposing_reads + bp2_opposing_reads
            total_oppose = len(set(all_op_reads))

            print("Found %s reads in support of variant" % total_support)
            print("Found %s reads opposing variant" % total_oppose)

            # if sv_type == 'DEL':
            #     supporting_reads = []
            #     del_support = Deletions(bam_in, chrom, bp1, bp2, slop, 'support', out_dir, supporting_reads, debug)
            #     bp1_sv_reads, bp1_read_count, bp2_sv_reads, bp2_read_count, total_support = del_support.get_reads()
            #     del_oppose  = Deletions(bam_in, chrom, bp1, bp2, slop, 'oppose', out_dir, total_support, debug)
            #     bp1_opposing_reads, bp1_opposing_read_count, bp2_opposing_reads, bp2_opposing_read_count, total_oppose = del_oppose.get_reads()
            #
            #
            # if sv_type == 'INV':
            #     supporting_reads = []
            #     inv_support = Inversions(bam_in, chrom, bp1, bp2, slop, 'support', out_dir, supporting_reads, debug)
            #     bp1_sv_reads, bp1_read_count, bp2_sv_reads, bp2_read_count, total_support = inv_support.get_reads()
            #     inv_oppose  = Inversions(bam_in, chrom, bp1, bp2, slop, 'oppose', out_dir, total_support, debug)
            #     bp1_opposing_reads, bp1_opposing_read_count, bp2_opposing_reads, bp2_opposing_read_count, total_oppose = inv_oppose.get_reads()


            #-------------------
            # Calculate af
            #-------------------

            allele_frequency = calculate_allele_freq(total_support, total_oppose, purity)
            # print("%s\t%s\t%s\t%s") % (chrom, bp1, bp2, allele_frequency)


        except IOError as err:
            sys.stderr.write("IOError " + str(err) + "\n");
            return

if __name__ == "__main__":
    sys.exit(main())
