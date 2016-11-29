=================
Filtered variants
=================

To view the results in excel, download the table using the links at the bottom of
the page

Candidate Somatic SNP variants
=======================================

The following tables present candidate somatic SNP variants.

.. report:: Filtered.Snp
   :render: table
   :large: xls
   :groupby: track
   :force:

For definition of column headings see below indel tables. 

Candidate Somatic INDEL variants
=======================================

The following tables present candidate somatic INDEL variants.

.. report:: Filtered.Indel
   :render: table
   :large: xls
   :groupby: track
   :force:

For definition of column headings see below. 


Definition of column headings:
REF = reference allele
ALT = alternate allele
Normal_Ref = frequency of normal allele in control sample
Normal_Alt = frequency of alternative allele in control sample
Tumor_Ref = frequency of normal allele in tumor sample
Tumor_Alt = frequency of alternative allele in tumor sample
Impact = expected impact of variant
SNPEFF_GENE_BIOTYPE = if available, eg. protein-coding, pseudogene
AA_change = amino acid change


SNP Filtering Summary
=======================================

The following tables present the filtering summaries for SNP
filtering. SNP may be filtered for a combination of justifications or
a single justification. The filtering summarised here applies only to
MuTect. Further filtering may be have applied downstream.

.. report:: Filtered.FilterSummary
   :render: table
   :large: xls
   :groupby: track
   :force:

   Filtering summary


Intersection heatmap
=======================================

The following plot presents the intersection (overlap) between
samples, expressed as the number of genes in both samples and the
percentage of genes in the intersection

.. report:: exomeReport.imagesTracker
   :render: gallery-plot
   :glob: intersection.dir/overlap_*_heatmap.png

   Intersection heatmap	   


Tables for download
=======================================

All candidate Somatic SNP variants
=======================================
.. report:: Filtered.Snp
   :render: xls-table
   :force:

All candidate Somatic INDEL variants
=======================================
.. report:: Filtered.Indel
   :render: xls-table
   :force:

Candidate Somatic SNP variants by patient ID
=======================================
.. report:: Filtered.Snp
   :render: xls-table
   :groupby: track
   :force:


Candidate Somatic INDEL variants by patient ID
=======================================
.. report:: Filtered.Indel
   :render: xls-table
   :groupby: track
   :force:

SNP Filtering Summary
=======================================
.. report:: Filtered.FilterSummary
   :render: xls-table
   :force:



