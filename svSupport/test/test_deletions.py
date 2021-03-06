import os, sys
import unittest
from svSupport.svSupport import worker
from svSupport.getReads import get_reads


root = os.path.dirname(os.path.abspath(__file__)) + "/data/"
bam_in = root + 'test.bam'
chrom = '3L'
bp1 = 9892365
bp2 = 9894889
slop = 500
out_dir = root + '../test_out/'
bp1_best_guess, bp2_best_guess = 'F_bp1', 'bp2_R'
debug=False

# reads = FindReads(bam_in, chrom, bp1, bp2, slop, out_dir, debug, bp1_best_guess, bp2_best_guess)
#
# class BreakpointReads(unittest.TestCase):
#     """Test reads returned in support of breakpoints"""
#     bp1_supporting_reads, bp1_support_count, bp1_support_bam, bp1_opposing_reads, bp1_oppose_count, bp1_oppose_bam = reads.bp1_reads()
#     bp2_supporting_reads, bp2_support_count, bp2_support_bam, bp2_opposing_reads, bp2_oppose_count, bp2_oppose_bam = reads.bp2_reads(bp1_supporting_reads, bp1_opposing_reads)
#
#     def test_bp1_read_count(self):
#         """Are the correct number of bp1 supporting reads reported?"""
#         self.assertTrue(self.bp1_support_count == 4)
#
#     def test_bp1_read_names(self):
#         """Are the correct bp1 supporting reads reported?"""
#         bp1_true_support = ['HWI-D00405:129:C6KNAANXX:4:1309:3990:94686', 'HWI-D00405:129:C6KNAANXX:4:1209:9222:18319',
#                             'HWI-D00405:129:C6KNAANXX:4:2304:19694:29523', 'HWI-D00405:129:C6KNAANXX:4:1314:2618:18304']
#         self.assertTrue(sorted(self.bp1_supporting_reads) == sorted(bp1_true_support))
#
#     def test_bp2_read_count(self):
#         """Are the correct number of bp2 supporting reads reported?"""
#         self.assertTrue(self.bp2_support_count == 2)
#
#     def test_bp2_read_names(self):
#         """Are the correct bp2 supporting reads reported?"""
#         bp2_true_support = ['HWI-D00405:129:C6KNAANXX:4:2209:8835:88441', 'HWI-D00405:129:C6KNAANXX:4:2308:11448:52099']
#
#         self.assertTrue(sorted(self.bp2_supporting_reads) == sorted(bp2_true_support))
#
#
# class OpposingReads(unittest.TestCase):
#     """Test reads returned that oppose breakpoints"""
#     bp1_supporting_reads, bp1_support_count, bp1_support_bam, bp1_opposing_reads, bp1_oppose_count, bp1_oppose_bam = reads.bp1_reads()
#     bp2_supporting_reads, bp2_support_count, bp2_support_bam, bp2_opposing_reads, bp2_oppose_count, bp2_oppose_bam = reads.bp2_reads(bp1_supporting_reads, bp1_opposing_reads)
#
#     def test_bp1_opposing_read_count(self):
#         """Are the correct number of bp1 opposing reads reported?"""
#         self.assertTrue(self.bp1_oppose_count == 5)
#
#
#     def test_bp1_opposing_read_names(self):
#         """Are the correct bp1 supporting reads reported?"""
#         bp1_true_opposing = ['HWI-D00405:129:C6KNAANXX:4:1308:17331:61532', 'HWI-D00405:129:C6KNAANXX:4:2104:6715:89377',
#                              'HWI-D00405:129:C6KNAANXX:4:1304:5668:41607', 'HWI-D00405:129:C6KNAANXX:4:2306:20091:19131',
#                              'HWI-D00405:129:C6KNAANXX:4:1206:21081:69455']
#
#         self.assertTrue(sorted(self.bp1_opposing_reads) == sorted(bp1_true_opposing))
#
#     def test_bp2_opposing_read_count(self):
#         """Are the correct number of bp1 opposing reads reported?"""
#         self.assertTrue(self.bp2_oppose_count == 11)
#
#     def test_bp2_opposing_read_names(self):
#         """Are the correct bp1 supporting reads reported?"""
#         bp2_true_opposing = ['HWI-D00405:129:C6KNAANXX:4:2214:19389:55608', 'HWI-D00405:129:C6KNAANXX:4:1213:10124:91137',
#                              'HWI-D00405:129:C6KNAANXX:4:1313:4501:44764', 'HWI-D00405:129:C6KNAANXX:4:1313:12748:63630',
#                              'HWI-D00405:129:C6KNAANXX:4:2301:4836:91092', 'HWI-D00405:129:C6KNAANXX:4:2101:7585:78240',
#                              'HWI-D00405:129:C6KNAANXX:4:1208:18379:99092', 'HWI-D00405:129:C6KNAANXX:4:2116:20962:76910',
#                              'HWI-D00405:129:C6KNAANXX:4:2306:8064:69868', 'HWI-D00405:129:C6KNAANXX:4:2108:10027:6512',
#                              'HWI-D00405:129:C6KNAANXX:4:2114:6250:93372']
#
#         self.assertTrue(sorted(self.bp2_opposing_reads) == sorted(bp2_true_opposing))
#
#
# class CalcFreq(unittest.TestCase):
#     """Test correct allele frequency is returned"""
#     def test_allele_frequency(self):
#         bp1_supporting_reads, bp1_support_count, bp1_support_bam, bp1_opposing_reads, bp1_oppose_count, bp1_oppose_bam = reads.bp1_reads()
#         bp2_supporting_reads, bp2_support_count, bp2_support_bam, bp2_opposing_reads, bp2_oppose_count, bp2_oppose_bam = reads.bp2_reads(bp1_supporting_reads, bp1_opposing_reads)
#
#         total_support = bp1_support_count + bp2_support_count
#         total_oppose = bp1_oppose_count + bp2_oppose_count
#         af = AlleleFrequency(total_oppose, total_support, 1, chrom)
#         allele_frequency = af.read_support_af()
#
#         self.assertTrue(float(allele_frequency) == 0.27)

if __name__ == '__main__':
    unittest.main()
