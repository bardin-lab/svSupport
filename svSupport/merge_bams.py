
import pysam
import os

def merge_bams(out_file, bams):
    in_files = ', '.join(bams)
    print("Merging bam files %s into '%s'") % (in_files, out_file)
    merge_parameters = ['-f', out_file] + bams
    pysam.merge(*merge_parameters)
    # Remove individual bp files
    for bp_file in bams:
        os.remove(bp_file)
        os.remove(bp_file + ".bai")

    pysam.index(out_file)
