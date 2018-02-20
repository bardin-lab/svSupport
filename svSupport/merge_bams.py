import pysam
import os
import ntpath

def merge_bams(out_file, out_dir, bams):
    s_bams = []
    for bam_file in bams:
        try:
            name = os.path.splitext(bam_file)[0]
            head, file_name = ntpath.split(bam_file)
            sorted_bam = os.path.join(out_dir, file_name + ".s" + ".bam")
            pysam.sort("-o", sorted_bam, bam_file)
            os.remove(bam_file)
            s_bams.append(sorted_bam)
        except:
            print("Can't sort %s" % bam_file)
        try:
            pysam.index(sorted_bam)
        except:
            print("Can't index %s" % sorted_bam)

    in_files = ', '.join(s_bams)
    print("Merging bam files %s into '%s'") % (in_files, out_file)
    merge_parameters = ['-f', out_file] + s_bams
    pysam.merge(*merge_parameters)

    #Remove individual bp files
    for bp_file in s_bams:
        try:
            abs_file = os.path.join(out_dir, bp_file)
            os.remove(abs_file)
            os.remove(abs_file + ".bai")
        except OSError:
            print("Couldn't remove %s" % abs_file)
            pass

    try:
        pysam.index(out_file)
    except pysam.utils.SamtoolsError:
        print("Can't index %s" % out_file)
        command = ' '.join(["samtools index ", out_file])
        try:
            print("Trying a shell call %s" % command)
            call(command, shell=True)
        except:
            print("Tried shell call in merge_bams: %s" % command)
            print("Can't index %s" % out_file)
            pass
