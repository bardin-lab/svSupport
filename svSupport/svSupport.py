#!/usr/bin/env python
from __future__ import division
import os, re, sys
sys.dont_write_bytecode = True
import pysam
import pandas as pd
from collections import defaultdict
from optparse import OptionParser
from find_reads import FindReads
from merge_bams import merge_bams
import ntpath
from count_reads import count_reads, region_depth

def parse_config(options):
    print
    print("Extracting arguments from config file: %s " % options.config)
    try:
        os.remove(options.variants_out)
        print("Cleaning up old variants file '%s'" % options.variants_out)
    except OSError:
        pass
    print

    out_file = options.variants_out
    af_out = open(out_file, 'w+')
    df=pd.read_csv(options.config,delimiter="\t")
    df = df.where((pd.notnull(df)), None)

    seen_events = defaultdict(int)

    for index, variant in df.iterrows():
        if variant['event']:
            key = '_'.join([variant['sample'], str(variant['event'])])
            seen_events[key] += 1

            if seen_events[key] > 1:
                print("Seen this event before: %s, %s") % (variant['sample'], str(variant['event']))
                continue

        options.in_file = variant['bam']
        options.region  = variant['locus']
        options.purity = float(variant['purity'])
        options.ratio_file = variant['read_depth']
        options.find_bps = True
        if variant['guess'] is not None:
            options.guess = True

        chrom, bp1, bp2, allele_frequency = worker(options)
        out_line = [variant['sample'], chrom, bp1, bp2, allele_frequency, variant['type'], variant['length(Kb)'], variant['bp1_locus'], variant['bp2_locus'], variant['affected_genes']  ]
        af_out.write('\t'.join(map(str, out_line)) + '\n')

    af_out.close()


def calculate_allele_freq(total_support, total_oppose, tumour_purity, depth):
    print("* Tumour purity set to %s" % tumour_purity)
    # if depth:
    #     allele_frequency = (1-average_ratio)
    #     print ("Deletion")
    # else:
    #     allele_frequency = 1-(1/average_ratio)
    #     print ("Duplication")
    allele_frequency = float( total_support/(total_support+total_oppose) )
    if tumour_purity == 1:
        adj_allele_frequency = allele_frequency
    else:
        adj_allele_frequency = float( total_support/( total_support + (total_oppose**tumour_purity) ) )

    allele_frequency = "{:.2f}".format(allele_frequency)
    adj_allele_frequency = "{:.2f}".format(adj_allele_frequency)
    print("* Adjusted allele frequency from %s to %s") % (allele_frequency, adj_allele_frequency)
    print
    return(adj_allele_frequency)


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
    if not read.is_proper_pair and (not read.is_reverse and read.reference_start + read.reference_length <= bp):
        return True

def bp_R(read, bp):
    if not read.is_proper_pair and (read.is_reverse and read.reference_start >= bp):
        return True

def bp_F(read, bp):
    if not read.is_proper_pair and (not read.is_reverse and read.reference_start >= bp):
        return True

def guess_type(bamFile, chrom, bp, bp_number, out_dir, debug):
    samfile = pysam.Samfile(bamFile, "rb")
    start = bp - 200
    stop = bp + 200

    sv_reads = defaultdict(int)

    print(bp, bp_number)
    count = 0
    out_file = os.path.join(out_dir, bp_number + "_classifying_reads" + ".bam")

    with pysam.AlignmentFile(out_file, "wb", template=samfile) as bpReads:

        for read in samfile.fetch(chrom, start, stop):

            if read.reference_start +1 == bp and re.findall(r'(\d+)[S|H]', read.cigarstring):
                if re.findall(r'.*?M(\d+)[S|H]', read.cigarstring):
                    # print("Read clipped to right: %s") % (read.cigarstring)
                    if bp_number == 'bp1':
                        sv_reads['F_bp1'] += 1
                        bpReads.write(read)
                    else:
                        sv_reads['F_bp2'] += 1
                        bpReads.write(read)
                elif re.findall(r'(\d+)[S|H].*?M', read.cigarstring):
                    # print("Read clipped to left: %s") % (read.cigarstring)
                    if bp_number == 'bp2':

                        sv_reads['bp2_R'] += 1
                        bpReads.write(read)
                    else:
                        sv_reads['bp1_R'] += 1
                        bpReads.write(read)

            elif bp_number == 'bp1':
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
                elif bp_F(read, bp):
                    sv_reads['bp2_F'] += 1
                    bpReads.write(read)


    pysam.index(out_file)
    sv_reads['NA'] = 0
    maxValKey = max(sv_reads, key=sv_reads.get)

    return(sv_reads, maxValKey)


def bedtools(filename):
    """simulate the behaviour of bedtools"""
    bamfile=pysam.AlignmentFile(filename,'rb')

    for ref in bamfile.header['SQ']:
        name=ref['SN']
        read_count = {}
        pileup=bamfile.pileup()
        for pos,column in enumerate(pileup,1):
            depth=column.nsegments
            print(name,pos,depth)
            read_count[name] += depth
            # if pos >= 10:
            #     break
    for c in read_count:
        print(c, read_count[c])

def get_depth(chrom, bp1, bp2, ratio_file, purity):
    count = 1
    cum_ratio = 0
    with open(ratio_file, 'r') as depth_ratios:
        for l in depth_ratios:
            parts = l.rstrip().split('\t')
            if parts[0] == 'Chromosome':
                continue

            pos = int(parts[1])
            ratio = float(parts[2]) * 2

            if parts[0] == chrom and pos >= bp1 and pos <= bp2:
                print(parts[:3])
                cum_ratio += ratio
                count += 1

        average_ratio = cum_ratio/count

        print("Average ratio: %s" % average_ratio)
        print("count: %s" % count)

        if average_ratio <= 1:
            allele_frequency = (1-abs(average_ratio))
            print ("Deletion")
        else:
            allele_frequency = 1-(1/abs(average_ratio))
            print ("Duplication")
        allele_frequency = "{:.2f}".format(allele_frequency)

        print("* Allele frequency derived from read depth ratio = %s") % (allele_frequency)
        return(allele_frequency)


# def get_depth(chrom, bp1, bp2, ratio_file, purity):
#     count = 1
#     cum_ratio = 0
#     cum_test = 0
#     cum_ref = 0
#     with open(ratio_file, 'r') as depth_ratios:
#         for l in depth_ratios:
#             parts = l.rstrip().split('\t')
#             if parts[0] == 'chromosome':
#                 continue
#
#             start = int(parts[1])
#             end = int(parts[2])
#             test = int(parts[3]) + 0.001
#             ref = int(parts[4]) + 0.001
#
#             if parts[0] == chrom and start >= bp1 and end <= bp2:
#                 ratio = float(test/ref)
#                 cum_ratio += ratio
#                 cum_test += float(parts[3])
#                 cum_ref += float(parts[4])
#                 count += 1
#         print(cum_test, count)
#
#         av_test = cum_test/count
#         av_ref = cum_ref/count
#
#         average_ratio = av_test/av_ref
#
#         print(average_ratio, av_test, av_ref)
#
#         # allele_frequency = calculate_allele_freq(av_test, av_ref, purity, depth=True)
#
#         if average_ratio <= 1:
#             allele_frequency = (1-average_ratio)
#             print ("Deletion")
#         else:
#             allele_frequency = 1-(1/average_ratio)
#             print ("Duplication")
#         allele_frequency = "{:.2f}".format(allele_frequency)
#
#         print("* Allele frequency derived from read depth ratio = %s") % (allele_frequency)
#         return(allele_frequency)


def hone_bps(bam_in, chrom, bp, bp_class):
    samfile = pysam.Samfile(bam_in, "rb")
    start = bp - 5
    stop = bp + 5
    original_breakpoint = int(bp)

    bp_reads = {}
    for i in range(start, stop):
        count = 0

        for read in samfile.fetch(chrom, i-1, i+1):
            read_end_pos   = read.reference_start + read.alen
            read_start_pos = read.reference_start

            if bp_class == 'F_bp1' or bp_class == 'F_bp2':
                if read_end_pos == i:
                    count += 1
                    bp_reads[i] = count

            elif bp_class == 'bp2_R' or bp_class == 'bp1_R':
                if read.reference_start +1 == i:
                    count += 1
                    bp_reads[i] = count


    try:
        maxValKey = max(bp_reads, key=bp_reads.get)
        read_count = bp_reads[maxValKey]
    except ValueError:
        print("Can't find split read support - using priovided breakpoints")
        maxValKey = original_breakpoint
        read_count = 0

    return(maxValKey, read_count)

def get_regions(bam_in, chrom, bp1, bp2, out_dir, slop):
    extender = slop * 2

    samfile = pysam.Samfile(bam_in, "rb")
    bp1_bam = os.path.join(out_dir, "bp1_region" + ".bam")

    with pysam.AlignmentFile(bp1_bam, "wb", template=samfile) as bp1_region:
        for read in samfile.fetch(chrom, bp1-extender, bp1+extender):
            bp1_region.write(read)

    bp2_bam = os.path.join(out_dir, "bp2_region" + ".bam")
    with pysam.AlignmentFile(bp2_bam, "wb", template=samfile) as bp2_region:
        for read in samfile.fetch(chrom, bp2-extender, bp2+extender):
            bp2_region.write(read)

    bps_bam = os.path.join(out_dir, "bp_regs" + ".bam")
    merge_bams(bps_bam, out_dir, [bp1_bam, bp2_bam])

    dups_rem = os.path.join(out_dir, "bp_regions" + ".bam")
    print(dups_rem)

    with pysam.AlignmentFile(dups_rem, "wb", template=samfile) as out:
        for read in samfile.fetch(chrom, bp1-extender, bp2+extender):
            if read.is_duplicate:
                continue
            out.write(read)

    head, file_name = ntpath.split(dups_rem)
    de_duped_bam = os.path.splitext(file_name)[0]

    sorted_bam = os.path.join(out_dir, de_duped_bam + ".s" + ".bam")
    pysam.sort("-o", sorted_bam, dups_rem)
    pysam.index(sorted_bam)

    return(sorted_bam)

def cleanup(out_dir):
    print("Cleaning up old files in %s" % out_dir)
    for f in os.listdir(out_dir):
        try:
            abs_file = os.path.join(out_dir, f)
            os.remove(abs_file)
        except OSError:
            print("Can't remove %s" % abs_file)
            pass

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

    parser.add_option("-c", \
                    "--config", \
                    dest="config",
                    action="store",
                    help="Config file for batch processing " + \
                         "sample\tchromosome:bp1-bp2\tpurity\type")

    parser.add_option("-v", \
                    "--variants", \
                    dest="variants_out",
                    action="store",
                    help="File to write parsed values to " )

    parser.add_option("-g", \
                    "--guess", \
                    dest="guess",
                    action="store_true",
                    help="Guess type of SV for read searching" )

    out_path = os.path.abspath('../out')
    parser.set_defaults(slop=500, out_dir=out_path, purity=1, variants_out='variants_out.txt')
    options, args = parser.parse_args()

    if (options.in_file is None or options.region is None) and options.test is False and options.config is None:
      parser.print_help()
      print

    return(options, args)


def worker(options):
    bam_in   = options.in_file
    region   = options.region
    slop     = options.slop
    out_dir  = options.out_dir
    debug    = options.debug
    purity   = float(options.purity)
    find_bps = options.find_bps
    test     = options.test
    ratio_file = options.ratio_file
    variants_out = options.variants_out
    guess = options.guess

    chrom, bp1, bp2 = re.split(':|-', region)
    bp1 = int(bp1)
    bp2 = int(bp2)
    slop = int(slop)

    if debug:
        print_options(bam_in, ratio_file, chrom, bp1, bp2, slop, find_bps, debug, test, out_dir)

    cleanup(out_dir)

    if options.config:
        if ratio_file is not None:
            print("python svSupport.py -i %s -r %s -l %s:%s-%s -s %s -p %s -f %s -o %s -v %s") % (bam_in, ratio_file, chrom, bp1, bp2, slop, purity, find_bps, out_dir, variants_out)
        else:
            print("python svSupport.py -i %s -l %s:%s-%s -s %s -p %s -f %s -o %s -v %s") % (bam_in, chrom, bp1, bp2, slop, purity, find_bps, out_dir, variants_out)

    if guess:
        bp1_reads, bp1_best_guess = guess_type(bam_in, chrom, bp1, 'bp1', out_dir, debug)
        bp1_best_guess = max(bp1_reads, key=bp1_reads.get)
        bp2_reads, bp2_best_guess = guess_type(bam_in, chrom, bp2, 'bp2', out_dir, debug)
        bp2_best_guess = max(bp2_reads, key=bp2_reads.get)

        if bp1_best_guess == 'F_bp1' and bp2_best_guess == 'bp2_R':
            print("Deletion")
            print("__\ bp1 ... bp2 /__")
        elif bp1_best_guess == 'F_bp1' and bp2_best_guess == 'F_bp2':
            print("Inversion type I")
            print("__\ bp1 ... __\ bp2")
        elif bp1_best_guess == 'bp1_R' and bp2_best_guess == 'bp2_R':
            print("Inversion type II")
            print("bp1 /__ ... bp2 /__")
        elif bp1_best_guess == 'bp1_R' and bp2_best_guess == 'F_bp2':
            print("Tandem duplication")
            print("bp1 /__ ... __\ bp2")
            bp1_best_guess, bp2_best_guess = 'F_bp1', 'bp2_R'
        else:
            print("-> Can't predict sv type - assuming deletion")
            print("__\ bp1 ... bp2 /__")
            bp1_best_guess, bp2_best_guess = 'F_bp1', 'bp2_R'

    else:
        bp1_best_guess, bp2_best_guess = 'F_bp1', 'bp2_R'

    print(bp1_best_guess, bp2_best_guess)

    if ratio_file is not None and ratio_file != 'NA':
        print("* Calculating allele frequency from read depth file: %s" % ratio_file)
        # allele_frequency = get_depth(chrom, bp1, bp2, ratio_file, purity)
        chromosomes = ['2L', '2R', '3L', '3R', '4', 'X', 'Y']
        reads_by_chrom, total_mapped = count_reads(ratio_file, chromosomes)
        print("Total number of mapped reads in %s: %s") % (ratio_file, total_mapped)
        read_count = region_depth(ratio_file, chrom, bp1, bp2)
        print("Reads in sv region: %s") % (read_count)

        allele_frequency = 0.9

        return(chrom, bp1, bp2, allele_frequency)
    else:
        if find_bps:
            bp1, bp1_count = hone_bps(bam_in, chrom, bp1, bp1_best_guess)
            bp2, bp2_count = hone_bps(bam_in, chrom, bp2, bp2_best_guess)

            print("* Bp1 adjusted to: %s [%s split reads found]") % (bp1, bp1_count)
            print("* Bp2 adjusted to: %s [%s split reads found]") % (bp2, bp2_count)

        make_dirs(bam_in, out_dir)

        bp_regions = get_regions(bam_in, chrom, bp1, bp2, out_dir, slop)

        reads = FindReads(bp_regions, chrom, bp1, bp2, slop, out_dir, debug, bp1_best_guess, bp2_best_guess)
        bp1_supporting_reads, bp1_support_count, bp1_support_bam, bp1_opposing_reads, bp1_oppose_count, bp1_oppose_bam = reads.bp1_reads()
        bp2_supporting_reads, bp2_support_count, bp2_support_bam, bp2_opposing_reads, bp2_oppose_count, bp2_oppose_bam = reads.bp2_reads(bp1_supporting_reads, bp1_opposing_reads)

        support_out = os.path.join(out_dir, "sv_support" + ".bam")
        oppose_out = os.path.join(out_dir, "sv_oppose" + ".bam")

        merge_bams(support_out, out_dir, [bp1_support_bam, bp2_support_bam])
        merge_bams(oppose_out, out_dir, [bp1_oppose_bam, bp2_oppose_bam])

        all_su_reads = bp1_supporting_reads + bp2_supporting_reads
        total_support = len(set(all_su_reads))

        all_op_reads = bp1_opposing_reads + bp2_opposing_reads
        total_oppose = len(set(all_op_reads))

        print("* Found %s reads in support of variant" % total_support)
        print("* Found %s reads opposing variant" % total_oppose)

        allele_frequency = calculate_allele_freq(total_support, total_oppose, purity, depth=False)
        return(chrom, bp1, bp2, allele_frequency)


# @profile
def main():
    options, args = get_args()

    if options.config is not None:
        parse_config(options)
        sys.exit()

    elif options.test is True:
        print
        print("* Running in test mode...")
        print

        options.region = '3L:9892365-9894889'
        options.out_dir = '../test_out'
        options.in_file = '../data/test.bam'
        options.debug = True

    if (options.in_file is not None and options.region is not None) or options.ratio_file is not None:
        try:
            chrom, bp1, bp2, allele_frequency = worker(options)
            return(chrom, bp1, bp2, allele_frequency)
        except IOError as err:
            sys.stderr.write("IOError " + str(err) + "\n");
            return

if __name__ == "__main__":
    sys.exit(main())
