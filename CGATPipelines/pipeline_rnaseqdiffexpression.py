##########################################################################
#
#   MRC FGU Computational Genomics Analysis & Training Programme
#
#   $Id$
#
#   Copyright (C) 2014 David Sims
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; either version 2
#   of the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
##########################################################################

"""========================================
RNA-Seq Differential expression pipeline
========================================

:Author: Andreas Heger
:Release: $Id$
:Date: |today|
:Tags: Python

The RNA-Seq differential expression pipeline performs differential
expression analysis. It requires three inputs:

   1. one or more genesets in :term:`gtf` formatted files
   2. mapped reads in :term:`bam` formatted files
   3. design files as :term:`tsv`-separated format

This pipeline works on a single genome.

Overview
========

The pipeline performs the following:

   * compute tag counts on an exon, transcript and gene level for each
     of the genesets. The following tag counting methods are implemented:
      * featureCounts_
      * gtf2table

   * estimate FPKM using cufflinks for each of the gene sets

   * perform differential expression analysis. The methods currently
     implemented are:

      * DESeq
      * EdgeR
      * Cuffdiff

Background
============

The quality of the rnaseq data (read-length, paired-end) determines
the quality of transcript models. For instance, if reads are short
(35bp) and/or reads are not paired-ended, transcript models will be
short and truncated.  In these cases it might be better to concentrate
the analysis on only previously known transcript models.

Transcripts are the natural choice to measure expression of. However
other quantities might be of interest. Some quantities are biological
meaningful, for example differential expression from a promotor shared
by several trancripts. Other quantities might no biologically
meaningful but are necessary as a technical comprise.  For example,
the overlapping transcripts might be hard to resolve and thus might
need to be aggregated per gene. Furthermore, functional annotation is
primarily associated with genes and not individual transcripts. The
pipeline attempts to measure transcription and differential expression
for a variety of entities following the classification laid down by
:term:`cuffdiff`:

isoform
   Transcript level
gene
   Gene level, aggregates several isoform/transcripts
tss
   Transcription start site. Aggregate all isoforms starting from the
   same :term:`tss`.
cds
   Coding sequence expression. Ignore reads overlapping non-coding
   parts of transcripts (UTRs, etc.). Requires annotation of the cds
   and thus only available for :file:`reference.gtf.gz`.

Methods differ in their ability to measure transcription on all
levels.

Overprediction of differential expression for low-level expressed
transcripts with :term:`cuffdiff` is a `known problem
<http://seqanswers.com/forums/showthread.php?t=6283&highlight=fpkm>`_.

Usage
=====

See :ref:`PipelineSettingUp` and :ref:`PipelineRunning` on general
information how to use CGAT pipelines.

Configuration
-------------

The pipeline requires a configured :file:`pipeline.ini` file.

The sphinxreport report requires a :file:`conf.py` and
:file:`sphinxreport.ini` file (see :ref:`PipelineReporting`). To start
with, use the files supplied with the Example_ data.

Input
-----

Reads
+++++

Reads are imported by placing :term:`bam` formatted files are linking
to files in the :term:`working directory`.

The default file format assumes the following convention::

   <samplename>.bam

Genesets
++++++++

Genesets are imported by placing :term:`gtf` formatted files in the
:term:`working directory`.

Design matrices
+++++++++++++++

Design matrices are imported by placing :term:`tsv` formatted files
into the :term:`working directory`. A design matrix describes the
experimental design to test. The design files should be named
design*.tsv.
Each design file has four columns::

      track   include group   pair
      CW-CD14-R1      0       CD14    1
      CW-CD14-R2      0       CD14    1
      CW-CD14-R3      1       CD14    1
      CW-CD4-R1       1       CD4     1
      FM-CD14-R1      1       CD14    2
      FM-CD4-R2       0       CD4     2
      FM-CD4-R3       0       CD4     2
      FM-CD4-R4       0       CD4     2

track
     name of track - should correspond to a sample name.
include
     flag to indicate whether or not to include this data
group
     group indicator - experimental group
pair
     pair that sample belongs to (for paired tests) - set to 0 if the
     design is not paired.

Optional inputs
+++++++++++++++

Requirements
------------

The pipeline requires the results from
:doc:`pipeline_annotations`. Set the configuration variable
:py:data:`annotations_database` and :py:data:`annotations_dir`.

On top of the default CGAT setup, the pipeline requires the following
software to be in the path:

+-----------+----------+----------------------------+
|*Program*  |*Version* |*Purpose*                   |
+-----------+----------+----------------------------+
|cufflinks_ |>=1.3.0   |transcription levels        |
+-----------+----------+----------------------------+
|samtools   |>=0.1.16  |bam/sam files               |
+-----------+----------+----------------------------+
|bedtools   |          |working with intervals      |
+-----------+----------+----------------------------+
|R/DESeq    |          |differential expression     |
+-----------+----------+----------------------------+

Pipeline output
===============

FPKM values
-----------

The directory :file:`fpkm.dir` contains the output of running
cufflinks_ against each set of reads for each geneset.

The syntax of the output files is ``<geneset>_<track>.cufflinks``. The
FPKM values are uploaded into tables as ``<geneset>_<track>_fpkm`` for
per-transcript FPKM values and ``<geneset>_<track>_genefpkm`` for
per-gene FPKM values.

Differential gene expression results
-------------------------------------

Differential expression is estimated for different genesets with a
variety of methods. Results are stored per method in subdirectories
such as :file:`deseq.dir`, :file:`edger.dir` or :file:`cuffdiff.dir`.

The syntax of the output files is ``<design>_<geneset>_...``.

:file:`.diff` files:
    The .diff files are :term:`tsv` formatted tables with the result
    of the differential expression analysis.

    The column names are:

    test_id
       gene_id/transcript_id/tss_id, etc
    treatment_name
       name of the treatment
    control_name
       name of the control
    !=_mean
       mean expression value of treatment/control
    !=_std
       standard deviation of treatment/control
    pvalue
       pvalue of test
    qvalue
       qvalue of test (FDR if the threshold was set at pvalue)
    l2fold
       log2 of fold change
    fold
       fold change, treatment / control
    significant
       flag: 1 if called significant
    status
       status of test. Values are
       OK: test ok, FAIL: test failed,
       NOCALL: no test (insufficient data, etc.).

The results are uploaded into the database as tables called
``<design>_<geneset>_<method>_<level>_<section>``.

Level denotes the biological entity that the differential analysis was
performed on.  Level can be one of ``cds``,``isoform``,``tss`` and
``gene``. The later should always be present.

Section is ``diff`` for differential expression results
(:file:`.diff`` files) and ``levels`` for expression levels.

.. note::

   For the pipeline to run, install the :doc:`pipeline_annotations` as well.

Glossary
========

.. glossary::

   cufflinks
      cufflinks_ - transcriptome analysis

   tophat
      tophat_ - a read mapper to detect splice-junctions

   deseq
      deseq_ - differential expression analysis

   cuffdiff
      find differentially expressed transcripts. Part of cufflinks_.

   cuffcompare
      compare transcriptomes. Part of cufflinks_.

.. _cufflinks: http://cufflinks.cbcb.umd.edu/index.html
.. _tophat: http://tophat.cbcb.umd.edu/
.. _bamstats: http://www.agf.liv.ac.uk/454/sabkea/samStats_13-01-2011
.. _deseq: http://www-huber.embl.de/users/anders/DESeq/
.. _featurecounts: http://bioinf.wehi.edu.au/featureCounts/

ChangeLog
=========

28.03.2014  Andreas Heger
            added automated selection of paired counting to featureCounts
            and gtf2table counting.

11.4.2014   Andreas Heger
            changed workflow. Multiple counters are applied and
            differential expression is computed on all.

15.10.2015  Charlotte George, Sebastian Luna-Valero
            SCRUM Oct 2015. Updating documentation.

Requirements:


Code
====

"""

# load modules
from ruffus import *
from ruffus.combinatorics import *

import CGAT.Experiment as E
import CGAT.Database as Database

import sys
import os
import itertools
import glob
import numpy
import pandas
import sqlite3
import CGAT.GTF as GTF
import CGAT.IOTools as IOTools
from rpy2.robjects import r as R
from rpy2.robjects.packages import importr
import rpy2.robjects as ro

import CGAT.BamTools as BamTools
import CGATPipelines.PipelineGeneset as PipelineGeneset
import CGATPipelines.PipelineRnaseq as PipelineRnaseq
import CGATPipelines.Pipeline as P
import CGATPipelines.PipelineTracks as PipelineTracks

# levels of cuffdiff analysis
# (no promotor and splice -> no lfold column)
CUFFDIFF_LEVELS = ("gene", "cds", "isoform", "tss")

###################################################
###################################################
###################################################
# Pipeline configuration
###################################################

# load options from the config file
P.getParameters(
    ["%s/pipeline.ini" % os.path.splitext(__file__)[0],
     "../pipeline.ini",
     "pipeline.ini"])

PARAMS = P.PARAMS
PARAMS.update(P.peekParameters(
    PARAMS["annotations_dir"],
    "pipeline_annotations.py",
    prefix="annotations_",
    update_interface=True,
    restrict_interface=True))

PipelineGeneset.PARAMS = PARAMS

Sample = PipelineTracks.AutoSample

# collect sra nd fastq.gz tracks
TRACKS = PipelineTracks.Tracks(Sample).loadFromDirectory(
    glob.glob("*.bam"), "(\S+).bam")

# group by experiment (assume that last field is a replicate identifier)
EXPERIMENTS = PipelineTracks.Aggregate(TRACKS, labels=("condition", "tissue"))

GENESETS = PipelineTracks.Tracks(Sample).loadFromDirectory(
    glob.glob("*.gtf.gz"), "(\S+).gtf.gz")


def connect():
    '''Connect to database (sqlite by default)

    This method also attaches to helper databases.
    '''

    dbh = sqlite3.connect(PARAMS["database_name"])
    statement = '''ATTACH DATABASE '%s' as annotations''' % (
        PARAMS["annotations_database"])
    cc = dbh.cursor()
    cc.execute(statement)
    cc.close()

    return dbh


# Expression levels: geneset vs bam files
TARGETS_FPKM = [(("%s.gtf.gz" % x.asFile(), "%s.bam" % y.asFile()),
                 "%s_%s.cufflinks" % (x.asFile(), y.asFile()))
                for x, y in itertools.product(GENESETS, TRACKS)]


@files(PARAMS["annotations_interface_geneset_all_gtf"],
       "geneset_mask.gtf")
def buildMaskGtf(infile, outfile):
    '''creates a gtf for cufflinks containing the transcripts you do not
    want to build transcript models of.

    This takes ensembl annotations (geneset_all.gtf.gz) and writes out
    all entries that have a 'source' match to "rRNA" or 'contig' match
    to "chrM" for use as a mask with cufflinks (see cufflinks manual
    for benefits of mask file
    http://cole-trapnell-lab.github.io/cufflinks/cufflinks/index.html).

    Parameters
    ----------

    infile : string
        :term:`gtf` file of ensembl annotations e.g. geneset_all.gtf.gz

    annotations_interface_table_gene_info : string
        :term:`PARAMS` gene_info table in annotations database - set
        in pipeline.ini in annotations directory

    annotations_interface_table_gene_stats : string
        :term:`PARAMS` gene_stats table in annotations database
        - set in pipeline.ini in annotations directory

    outfile : string

        A :term:`gtf` file for use as "mask file" for cufflinks.  This
        is created by filtering infile for certain transcripts e.g.
        rRNA or chrM transcripts and writing them to outfile

    '''

    dbh = connect()

    try:
        select = dbh.execute("""SELECT DISTINCT gene_id FROM %s
        WHERE gene_biotype = 'rRNA';""" % os.path.basename(
            PARAMS["annotations_interface_table_gene_info"]))
        rrna_list = [x[0] for x in select]
    except sqlite3.OperationalError as e:
        E.warn("can't select rRNA annotations, error='%s'" % str(e))
        rrna_list = []

    try:
        select2 = dbh.execute("""SELECT DISTINCT gene_id FROM %s
        WHERE contig = 'chrM';""" % os.path.basename(
            PARAMS["annotations_interface_table_gene_stats"]))
        chrM_list = [x[0] for x in select2]
    except sqlite3.OperationalError as e:
        E.warn("can't select rRNA annotations, error='%s'" % str(e))
        chrM_list = []

    geneset = IOTools.openFile(infile)
    outf = IOTools.openFile(outfile, "wb")
    for entry in GTF.iterator(geneset):
        if entry.gene_id in rrna_list or entry.gene_id in chrM_list:
            outf.write("\t".join((map(
                str,
                [entry.contig, entry.source, entry.feature,
                 entry.start, entry.end, ".", entry.strand,
                 ".", "transcript_id" + " " + '"' +
                 entry.transcript_id + '"' + ";" + " " +
                 "gene_id" + " " + '"' + entry.gene_id + '"']))) + "\n")

    outf.close()


@P.add_doc(PipelineGeneset.loadGeneStats)
@transform("*.gtf.gz",
           suffix(".gtf.gz"),
           "_geneinfo.load")
def loadGeneSetGeneInformation(infile, outfile):
    # Docs for this function linked to PipelineGeneset; please look there.
    PipelineGeneset.loadGeneStats(infile, outfile)


@P.add_doc(PipelineRnaseq.runCufflinks)
@follows(mkdir("fpkm.dir"))
@files([(x, os.path.join("fpkm.dir", y)) for x, y in TARGETS_FPKM])
def runCufflinks(infiles, outfile):
    '''estimate expression levels in each set using cufflinks.

    cufflinks output stored in fpkm.dir '''
    PipelineRnaseq.runCufflinks(
        infiles[0], infiles[1], outfile,
        job_threads=PARAMS["cufflinks_threads"])


@P.add_doc(PipelineRnaseq.loadCufflinks)
@transform(runCufflinks,
           suffix(".cufflinks"),
           ".load")
def loadCufflinks(infile, outfile):
    '''load expression level measurements into database.'''
    PipelineRnaseq.loadCufflinks(infile, outfile)


@P.add_doc(PipelineRnaseq.mergeCufflinksFPKM)
@collate(runCufflinks,
         regex("fpkm.dir/(.*)_(.*).cufflinks"),
         r"fpkm.dir/\1_fpkm_genes.tsv.gz")
def mergeCufflinksGeneFPKM(infiles, outfile):
    '''build aggregate table with cufflinks FPKM values.

        Takes cufflinks results from sample.genes_tracking.gz and 
        builds summary "_fpkm_genes.tsv.gz" in "fpkm.dir"'''
    PipelineRnaseq.mergeCufflinksFPKM(
        infiles,
        outfile,
        GENESETS,
        identifier="gene_id",
        tracking="genes_tracking")


@P.add_doc(PipelineRnaseq.mergeCufflinksFPKM)
@collate(runCufflinks,
         regex("fpkm.dir/(.*)_(.*).cufflinks"),
         r"fpkm.dir/\1_fpkm_isoforms.tsv.gz")
def mergeCufflinksIsoformFPKM(infiles, outfile):
    '''build aggregate table with cufflinks FPKM values.

        Takes cufflinks results from sample.fpkm_tracking.gz and 
        builds summary "_fpkm_isoforms.tsv.gz" in "fpkm.dir"'''
    PipelineRnaseq.mergeCufflinksFPKM(
        infiles,
        outfile,
        GENESETS,
        identifier="transcript_id",
        tracking="fpkm_tracking")


#########################################################################
#########################################################################
#########################################################################


@transform((mergeCufflinksGeneFPKM, mergeCufflinksIsoformFPKM),
           suffix(".tsv.gz"),
           ".load")
def loadCufflinksFPKM(infile, outfile):
    '''Loads merged fkpm data into table in database.

    Takes merged cufflinks fpkm :term:`tsv` files (e.g. 
    "refcoding_fpkm_genes.tsv.gz" or "refcoding_fpkm_isoforms.tsv.gz") and 
    loads fpkm data across samples for genes or isoforms into 
    "refcoding_fpkm_genes" or "refcoding_fpkm_isoforms" database tables. 

    Parameters
    ----------
    infile : string 
        refers to :term:`tsv`.gz file generated from cufflinks fpkm
        output files (e.g "refcoding_fpkm_genes.tsv.gz" or 
        "refcoding_fpkm_isoforms.tsv.gz")

    outfile : string
        creates infile.load to detail information loaded into database 
        tables'''

    P.load(infile, outfile,
           "--add-index=gene_id --add-index=transcript_id")


@merge(PARAMS["annotations_interface_geneset_all_gtf"],
       "coding_exons.gtf.gz")
def buildCodingExons(infile, outfile):
    '''Compile set of protein coding exons.

    This set is used for splice-site validation
    THIS FUNCTION IS NOT CALLED ANYWHERE IN PIPELINE
    '''

    statement = '''
    zcat %(infile)s
    | awk '$3 == "CDS"'
    | python %(scriptsdir)s/gtf2gtf.py
    --method=filter
    --filter-method=proteincoding
    --log=%(outfile)s.log
    | perl -p -e "s/CDS/exon/"
    | python %(scriptsdir)s/gtf2gtf.py
    --method=merge-exons
    --log=%(outfile)s.log
    | gzip
    > %(outfile)s
    '''
    P.run()

#########################################################################
#########################################################################
#########################################################################


@transform("*.gtf.gz",
           suffix(".gtf.gz"),
           ".unionintersection.bed.gz")
def buildUnionIntersectionExons(infile, outfile):
    '''build union/intersection genes according to
    Bullard et al. (2010) BMC Bioinformatics.

    Builds a single-segment bed file.
    THIS FUNCTION IS NOT CALLED ANYWHERE IN PIPELINE
    '''

    statement = '''
    gunzip < %(infile)s
    | python %(scriptsdir)s/gtf2gtf.py
    --method=intersect-transcripts
    --log=%(outfile)s.log
    | python %(scriptsdir)s/gff2gff.py
    --is-gtf
    --method=crop-unique
    --log=%(outfile)s.log
    | python %(scriptsdir)s/gff2bed.py --is-gtf --log=%(outfile)s.log
    | sort -k1,1 -k2,2n
    | gzip
    > %(outfile)s
    '''

    P.run()

#########################################################################
#########################################################################
#########################################################################


@transform("*.gtf.gz",
           suffix(".gtf.gz"),
           ".union.bed.gz")
def buildUnionExons(infile, outfile):
    '''build union genes.

    Exons across all transcripts of a gene are merged.
    They are then intersected between genes to remove any overlap.

    Builds a single-segment bed file.
    THIS FUNCTION IS NOT CALLED ANYWHERE IN PIPELINE
    '''

    statement = '''
    gunzip < %(infile)s
    | python %(scriptsdir)s/gtf2gtf.py
    --method=merge-exons
    --log=%(outfile)s.log
    | python %(scriptsdir)s/gff2gff.py
    --is-gtf
    --method=crop-unique
    --log=%(outfile)s.log
    | python %(scriptsdir)s/gff2bed.py
    --is-gtf
    --log=%(outfile)s.log
    | sort -k1,1 -k2,2n
    | gzip
    > %(outfile)s
    '''

    P.run()

#########################################################################
#########################################################################
#########################################################################


@follows(mkdir("genecounts.dir"))
@files([(("%s.bam" % x.asFile(), "%s.gtf.gz" % y.asFile()),
         ("genecounts.dir/%s.%s.tsv.gz" % (x.asFile(), y.asFile())))
        for x, y in itertools.product(TRACKS, GENESETS)])
def buildGeneLevelReadCounts(infiles, outfile):
    '''compute read counts and coverage of exons with reads.

    Takes a list of :term:`bam` files defined in "TRACKS" paired with
    :term:`gtf` files specified in "GENESETS" and produces `.tsv.gz`
    file using gtf2table.py detailing coverage of exonic reads for
    each bam.  The :term:`gtf` file is used to define exonic regions
    and a ".log" file is also produced for each input file.

    .. note::
        This ignores multimapping reads

    Parameters
    ----------

    infiles : list
        Takes a list of pairs of :term:`bam` file of aligned reads with
        :term:`gtf` files

    outfile : string
        Creates a compressed :term:`tsv` file (`tsv.gz`) containing
        coverage statistics of reads from :term:`bam` file and their
        coverage in regions defined by thee:term:`gtf` file

    '''

    bamfile, exons = infiles

    if BamTools.isPaired(bamfile):
        counter = 'readpair-counts'
    else:
        counter = 'read-counts'

    # ignore multi-mapping reads
    statement = '''
    zcat %(exons)s
    | python %(scriptsdir)s/gtf2table.py
          --reporter=genes
          --bam-file=%(bamfile)s
          --counter=length
          --column-prefix="exons_"
          --counter=%(counter)s
          --column-prefix=""
          --counter=read-coverage
          --column-prefix=coverage_
          --min-mapping-quality=%(counting_min_mapping_quality)i
          --multi-mapping-method=ignore
          --log=%(outfile)s.log
    | gzip
    > %(outfile)s
    '''
    job_memory = "4G"

    P.run()


@transform(buildGeneLevelReadCounts,
           suffix(".tsv.gz"),
           "_genecounts.load")
def loadGeneLevelReadCounts(infile, outfile):
    ''' Loads _genecounts table into database.

    Takes :term:`tsv` file containing gene level read count
    information (e.g. exon coverage statisitics from buildGeneLevelReadCounts)
    and loads as "_genecounts" table into database.

    Parameters
    ----------

    infile : string
        takes infile, a :term:`tsv` file containing gene level read count 
        information e.g. exon coverage statisitics from buildGeneLevelReadCounts
    outfile: string
        creates `.load` file for each input file detailing loading of information
        into "_genecounts" table in database'''

    P.load(infile, outfile, options="--add-index=gene_id")


@collate(buildGeneLevelReadCounts,
         regex("genecounts.dir/([^.]+)\.([^.]+).tsv.gz"),
         r"genecounts.dir/\2.genecounts.tsv.gz")
def aggregateGeneLevelReadCounts(infiles, outfile):
    ''' build a matrix of counts with genes and tracks dimensions 

    Takes a list of :term:`tsv` detailing coverage statisitics from 
    buildGeneLevelReadCounts for each sample and builds a matrix of counts 
    with genes and tracks dimenisions summarising all samples (i.e. tracks) 
    in outfile (e.g. "refcoding.genecounts.tsv.gz") using combine_tables.py.
    Outfile also has accompanying ".log" file.

    .. note::
        THIS USES ANYSENSE UNIQUE COUNTS - THIS NEEDS TO BE PARAMTERISED 
        FOR STRANDED/UNSTRANDED RNASEQ DATA


    Parameters
    ----------

    infiles : list        
        list of :term:`tsv` files detailing coverage statisitics from 
        buildGeneLevelReadCounts 
    outfile : string
        names the output files "genecounts.tsv.gz" output files are:        

        1. ".genecounts.tsv.gz" :term:`tsv` file containing matrix 
        of genes (rows) and counts per sample/track (columns).

        2. ".genecounts.tsv.gz.log"'''

    infiles = " ".join(infiles)
    # use anysense unique counts, needs to parameterized
    # for stranded/unstranded rnaseq data
    statement = '''python %(scriptsdir)s/combine_tables.py
    --columns=1
    --take=%(counting_type)s
    --use-file-prefix
    --regex-filename='([^.]+)\..+.tsv.gz'
    --log=%(outfile)s.log
    %(infiles)s
    | sed 's/geneid/gene_id/'
    | gzip > %(outfile)s '''

    P.run()


@follows(mkdir("extension_counts.dir"))
@transform("*.bam",
           regex(r"(\S+).bam"),
           r"extension_counts.dir/\1.extension_counts.tsv.gz")
def buildGeneLevelReadExtension(infile, outfile):
    '''compute extension of cds.

    Computes coverage within :term:`bam` file of extension of cds and
    known UTRs using gtf2table.py. Creates ".extension_counts.tsv.gz"
    for each input track.  Will remove "remove_contigs" specified in
    pipeline.ini.

    Counters used in gtf2table.py:

    * read-extension: This counter outputs the read density in bins upstream, 
      within and downstream of transcript models. The counter can be used to 
      predict the length of the 3' and 5' UTR.

    * position: output genomic coordinates of transcript/gene 
    (chromosome, start, end)

    Parameters
    ----------

    infile : string
        A :term:`bam` file containing aligned reads to enable calculation of 
        coverage over the cds

    annotations_interface_geneset_cds_gtf : string
        :term:`PARAMS` _geneset_cds.gtf.gz. 
        This is set in pipeline.ini in annotations directory

    annotations_interface_territories_gff : string
        :term:`PARAMS` refering to territories.gff.gz. 
        This is set in pipeline.ini in annotations directory

    annotations_interface_annotation_gff : string
        :term:`PARAMS` refering to annotation.gff.gz. 
        This is set in pipeline.ini in annotations directory

    outfile : string 
        A "extension_counts.tsv.gz" file. A :term:`tsv` file detailing coverage 
        of reads over the extension of the cds

    '''

    cds = PARAMS["annotations_interface_geneset_cds_gtf"]
    territories = PARAMS["annotations_interface_territories_gff"]
    utrs = PARAMS["annotations_interface_annotation_gff"]

    if "geneset_remove_contigs" in PARAMS:
        remove_contigs = '''| awk '$1 !~ /%s/' ''' % PARAMS[
            "geneset_remove_contigs"]
    else:
        remove_contigs = ""

    statement = '''
    zcat %(cds)s
    %(remove_contigs)s
    | python %(scriptsdir)s/gtf2table.py
          --reporter=genes
          --bam-file=%(infile)s
          --counter=position
          --counter=read-extension
          --min-mapping-quality=%(counting_min_mapping_quality)i
          --output-filename-pattern=%(outfile)s.%%s.tsv.gz
          --gff-file=%(territories)s
          --gff-file=%(utrs)s
          --log=%(outfile)s.log
    | gzip
    > %(outfile)s
    '''

    P.run()


#########################################################################
#########################################################################
#########################################################################


@follows(mkdir("transcriptcounts.dir"))
@files([(("%s.bam" % x.asFile(), "%s.gtf.gz" % y.asFile()),
         ("transcriptcounts.dir/%s.%s.tsv.gz" % (x.asFile(), y.asFile())))
        for x, y in itertools.product(TRACKS, GENESETS)])
def buildTranscriptLevelReadCounts(infiles, outfile):
    '''count reads falling into transcripts of protein coding gene models.

    Takes lists of :term:`bam` and :term:`gtf` files and pairs these
    up.  Counts the number of reads from each :term:`bam` file falling
    into transcript models specified in :term:`gtf` files using
    `gtf2table.py`.  These are saved as `tsv.gz` file in the
    `transcriptcounts.dir`

    Automatically detects if bam file is paired and uses
    "readpair-counts" as counter in to `gtf2table.py` if true. If
    single-end data `gtf2table.py` uses 'read-counts' as counter for
    `gtf2table.py`.See `gtf2table.py` for expalination of counters
    being used.

    Counters are:

    1. length
    2. readpair-counts / read-counts
    3. read-coverage

    Parameters
    ----------
    infiles : list
        A list of :term:`bam` - :term:`gtf` pairs. :term:`bam` files contain 
            aligned reads, :term:`gtf` files files contain the gene models 

    outfile : string
        Name of a :term:`tsv` file containing counts of reads falling within 
        gene models. Also names accompanying ".log" file

    '''
    bamfile, geneset = infiles

    if BamTools.isPaired(bamfile):
        counter = 'readpair-counts'
    else:
        counter = 'read-counts'

    statement = '''
    zcat %(geneset)s
    | python %(scriptsdir)s/gtf2table.py
          --reporter=transcripts
          --bam-file=%(bamfile)s
          --counter=length
          --column-prefix="exons_"
          --counter=%(counter)s
          --column-prefix=""
          --counter=read-coverage
          --column-prefix=coverage_
          --min-mapping-quality=%(counting_min_mapping_quality)i
          --multi-mapping-method=ignore
          --log=%(outfile)s.log
    | gzip
    > %(outfile)s
    '''

    P.run()


@transform(buildTranscriptLevelReadCounts,
           suffix(".tsv.gz"),
           ".load")
def loadTranscriptLevelReadCounts(infile, outfile):
    '''loads "tsv.gz" files from buildTranscriptLevelReadCounts into database
    table

    For example - the output from buildTranscriptLevelReadCounts
    `Brain-F1-R1.refcoding.tsv.gz` would be loaded into database as
    `Brain_F1_R1_refcoding` and a `Brain-F1-R1.refcoding.load file
    would be created.

    Parameters
    ----------
    infile : string
        denotes the `tsv.gz` file from buildTranscriptLevelReadCounts that will
        be loaded into database

    outfile : string
        names the `.load` file in the transcriptcounts.dir
        that details the information loaded into the database

    '''

    P.load(infile, outfile, options="--add-index=transcript_id")


@collate(buildTranscriptLevelReadCounts,
         regex("transcriptcounts.dir/([^.]+)\.([^.]+).tsv.gz"),
         r"transcriptcounts.dir/\2.transcriptcounts.tsv.gz")
def aggregateTranscriptLevelReadCounts(infiles, outfile):
    '''build a matrix of counts with transcripts and tracks dimensions

    Takes a list of :term:`tsv` detailing coverage statisitics from
    buildTranscriptLevelReadCounts for each sample and builds a matrix
    of counts with transcripts and tracks dimenisions summarising all
    samples (i.e. tracks) in outfile
    (e.g. "refcoding.transcriptcounts.tsv.gz") using
    combine_tables.py.  Outfile also has accompanying ".log" file.

    .. note::
        THIS USES ANYSENSE UNIQUE COUNTS - THIS NEEDS TO BE PARAMTERISED
        FOR STRANDED/UNSTRANDED RNASEQ DATA


    Parameters
    ----------

    infiles : list
        list of :term:`tsv` files detailing coverage statisitics from
        buildTranscriptLevelReadCounts
    outfile : string
        names the output files "transcriptcounts.tsv.gz" output files are:        

        1. ".transcriptcounts.tsv.gz" :term:`tsv` file containing matrix
        of transcripts (rows) and counts per sample/track (columns).

        2. ".transcriptcounts.tsv.gz.log"

    '''

    infiles = " ".join(infiles)
    # use anysense unique counts, needs to parameterized
    # for stranded/unstranded rnaseq data
    statement = '''python %(scriptsdir)s/combine_tables.py
    --columns=1
    --take=%(counting_type)s
    --use-file-prefix
    --regex-filename='([^.]+)\..+.tsv.gz'
    --log=%(outfile)s.log
    %(infiles)s
    | sed 's/transcriptid/transcript_id/'
    | gzip > %(outfile)s '''

    P.run()


@follows(mkdir("featurecounts.dir"))
@files([(("%s.bam" % x.asFile(), "%s.gtf.gz" % y.asFile()),
         ("featurecounts.dir/%s.%s.tsv.gz" % (x.asFile(), y.asFile())))
        for x, y in itertools.product(TRACKS, GENESETS)])
def buildFeatureCounts(infiles, outfile):
    '''counts reads falling into "features", which by default are genes.

    A read overlaps if at least one bp overlaps.

    Pairs and strandedness can be used to resolve reads falling into
    more than one feature. Reads that cannot be resolved to a single
    feature are ignored.

    Output is sent to featurecounts.dir

    See feature counts manual http://bioinf.wehi.edu.au/featureCounts/
    for information about :term:`PARAMS` options

    Parameters
    ----------
    infiles : list
        Two lists of file names, one containing list of :term:`bam` files with 
        the aligned reads, the second containing a list of :term:`gtf` files 
        containing the "features" to be counted.
    featurecounts_threads : int
        :term:`PARAMS` - number of threads to run feature counts. This is 
        specified in pipeline.ini
    featurecounts_strand : int
        :term:`PARAMS` - see feature counts --help for details of how to set 
    featurecounts_options : string
        :term:`PARAMS` - options for running feature counts, set using 
        pipeline.ini See feature counts --help for details of how to set 
    outfile : string
        used to denote output files from feature counts. Three output files are 
        produced for each input :term:`bam` - :term:`gtf` pair. These are:

        * input_bam.input_gtf.tsv.gz: contains list of gene id's and counts 
        * input_bam.input_gtf.tsv.summary: contains summary of reads counted
        * input_bam.input_gtf.tsv.log: log file produced by feature counts

    '''
    bamfile, annotations = infiles
    PipelineRnaseq.runFeatureCounts(
        annotations,
        bamfile,
        outfile,
        job_threads=PARAMS['featurecounts_threads'],
        strand=PARAMS['featurecounts_strand'],
        options=PARAMS['featurecounts_options'])


@collate(buildFeatureCounts,
         regex("featurecounts.dir/([^.]+)\.([^.]+).tsv.gz"),
         r"featurecounts.dir/\2.featurecounts.tsv.gz")
def aggregateFeatureCounts(infiles, outfile):
    ''' Build a matrix of counts with genes and tracks dimensions.

    Uses `combine_tables.py` to combine all the `tsv.gz` files output from 
    buildFeatureCounts into a single :term:`tsv` file named
    "featurecounts.tsv.gz". A `.log` file is also produced. 

    .. note::
        This uses column 7 as counts This is a possible source of bugs, the
        column position has changed before.

    Parameters
    ---------
    infiles : list
        a list of `tsv.gz` files from the feature_counts.dir that were the 
        output from feature counts
    outfile : string
        a filename denoting the file containing a matrix of counts with genes as
        rows and tracks as the columns - this is a `tsv.gz` file        '''

    infiles = " ".join(infiles)
    statement = '''python %(scriptsdir)s/combine_tables.py
    --columns=1
    --take=7
    --use-file-prefix
    --regex-filename='([^.]+)\..+.tsv.gz'
    --log=%(outfile)s.log
    %(infiles)s
    | sed 's/geneid/gene_id/'
    | gzip
    > %(outfile)s '''

    P.run()


@transform(aggregateFeatureCounts,
           suffix(".tsv.gz"),
           ".load")
def loadFeatureCounts(infile, outfile):
    '''Load aggregated feature counts into database.

    Load the aggregted feature counts of all tracks into a database table.
    For example "refcoding.featurecounts.tsv.gz" will be table
    "refcoding_featurecounts" in database.

    Parameters
    ----------
    infile : string
        filename of aggregated feature counts (e.g. `featurecounts.tsv.gz`).
    outfile : string
        filename of `.load` file summarising information loaded into
        database table'''

    P.load(infile, outfile, "--add-index=gene_id")


@merge(buildFeatureCounts,
       "featurecounts_summary.load")
def loadFeatureCountsSummary(infiles, outfile):
    '''Load feature counts summary data into table.

    Merge and load the summary files produced by "feature counts" into a 
    "featurecounts_summary" database table.

    Parameters
    ----------
    infile : list
        list of filenames used to detect summary file from feature counts output
    outfile : string
        filename of `featurecounts_summary.load` file summarising information
         loaded into database table
    '''
    infiles = [P.snip(x, ".gz") + ".summary" for x in infiles]
    P.mergeAndLoad(infiles, outfile, options="--add-index=track")


@transform((
    aggregateTranscriptLevelReadCounts,
    aggregateGeneLevelReadCounts,
    aggregateFeatureCounts),
           suffix(".tsv.gz"),
           ".stats.tsv.gz")
def summarizeCounts(infile, outfile):
    '''perform summarization of read counts

    takes `tsv.gz` files summarizing "feature counts" output and
    "gtf2table" genecounts output across all tracks and generates
    several different summary statistics and plots on the read count
    data using `runExpression.py`.

    Parameters
    ----------
    infile : string
        filename of aggregated "feature counts" counts
        (e.g. `featurecounts.tsv.gz`)
    infile : string
        filename of aggregated "gtf2table.py" counts (e.g. `genecounts.tsv.gz`)
    outfile : string
        filenames of output files detailing summary statistics

    * `output_file.stats_max_counts.tsv.gz`: details max counts and frequency
    * `output_file.stats_correlation.tsv`: summary of correlations between samples
    * `output_file.stats_scatter.png`: scatterplots and correlations
    * `output_file.stats_heatmap.svg`: heatmap of sample clustering
    * `output_file.stats_pca.svg`: principal component plot
    * `output_file.stats_mds.svg`: multidimensional scaling plot
    * `output_file.stats.tsv.gz.log`: log file
    * `output_file.stats.tsv.gz`: summarises row statitics for matrix in `tsv.gz` input file

    '''

    prefix = P.snip(outfile, ".tsv.gz")
    job_memory = "32G"
    statement = '''python %(scriptsdir)s/runExpression.py
    --method=summary
    --tags-tsv-file=%(infile)s
    --output-filename-pattern=%(prefix)s_
    --log=%(outfile)s.log
    | gzip
    > %(outfile)s'''
    P.run()


@follows(mkdir("designs.dir"))
@product("design*.tsv",
         formatter(".*/(?P<PART1>.*).tsv$"),
         (aggregateGeneLevelReadCounts,
          aggregateFeatureCounts),
         formatter(".*/(?P<PART2>.*).tsv.gz$"),
         "designs.dir/{PART1[0][0]}.{PART2[1][0]}.stats.tsv")
def summarizeCountsPerDesign(infiles, outfile):
    '''perform summarization of read counts within experiments.

    takes `tsv.gz` files summarizing "feature counts" output and "gtf2table" 
    genecounts output across all tracks, grouped as specified by `design*.tsv` 
    design file and generates several different summary statistics and plots 
    for each design on the read count data using `runExpression.py`. 


    Parameters
    ----------
    infiles : list
        list of filenames of `tsv.gz` files from "feature counts" counts 
        (e.g. `featurecounts.tsv.gz`) or "gtf2table.py" counts files to be 
        aggregated into experiments as specified by design file. Outputs are 
        stored in designs.dir 

    outfile : string
        filenames of output files detailing summary statistics 

            * `output_file.stats_max_counts.tsv.gz`: details max counts and frequency
            * `output_file.stats_correlation.tsv`: summary of correlations between samples
            * `output_file.stats_scatter.png`: scatterplots and correlations
            * `output_file.stats_heatmap.svg`: heatmap of sample clustering
            * `output_file.stats_pca.svg`: principal component plot
           * `output_file.stats_mds.svg`: multidimensional scaling plot
            * `output_file.stats.tsv.gz.log`: log file 
            * `output_file.stats.tsv.gz`: summarises row statitics for matrix in `tsv.gz` input file   '''

    design_file, counts_file = infiles
    prefix = P.snip(outfile, ".tsv")
    statement = '''python %(scriptsdir)s/runExpression.py
              --method=summary
              --design-tsv-file=%(design_file)s
              --tags-tsv-file=%(counts_file)s
              --output-filename-pattern=%(prefix)s_
              --log=%(outfile)s.log
              > %(outfile)s'''
    P.run()


@transform((summarizeCounts,
            summarizeCountsPerDesign),
           suffix(".stats.tsv"),
           "_stats.load")
def loadTagCountSummary(infile, outfile):
    '''loads summary of summarizeCounts and summarizeCountsPerDesign into 
    database.

    takes filename of ".stats.tsv" files in designs.dir and loads `_correlation`
    and `_stats` tables into database 

    Parameters
    ----------
    infile : string
        takes filename of ".stats.tsv" files in designs.dir 
    outfile : string
        filename specifying following created files and tables in database

        * _correlation.load file
        * _stats.load file
        * `_correlation` database table
        * `_stats` database table
'''
    P.load(infile, outfile)
    P.load(P.snip(infile, ".tsv") + "_correlation.tsv",
           P.snip(outfile, "_stats.load") + "_correlation.load",
           options="--first-column=track")


@follows(loadTagCountSummary,
         loadFeatureCounts,
         loadFeatureCountsSummary,
         loadTranscriptLevelReadCounts,
         aggregateGeneLevelReadCounts,
         aggregateFeatureCounts)
@transform((summarizeCounts,
            summarizeCountsPerDesign),
           suffix("_stats.tsv"), "_stats.load")
def counting():
    ''' collects output from  "feature counts" and "gtf2table.py" '''
    pass


@follows(mkdir("deseq.dir"), counting)
@product("design*.tsv",
         formatter("(.*).tsv$"),
         (aggregateGeneLevelReadCounts,
          aggregateFeatureCounts),
         formatter("(.*).tsv.gz$"),
         "deseq.dir/{basename[0][0]}.{basename[1][0]}.gz")
def runDESeq(infiles, outfile):
    '''Perform differential expression analysis using Deseq.

    Parameters
    ----------
    infiles: list
        list of input filenames

    infiles[0]: str
        Filename with experimental design in :term:`tsv` format

    infiles[1]: str
        filename of file containing tag counts in :term:`tsv` format

    deseq_fdr: float
        :term:`PARAMS`
        minimum acceptable fdr for deseq

    deseq_fit_type: str
        :term:`PARAMS`
        fit type to estimate dispersion with deseq.
        refer to
        https://bioconductor.org/packages/release/bioc/manuals/DESeq/man/DESeq.pdf

    deseq_dispersion_method: str
        :term:`PARAMS`
        method to estimate dispersion with deseq
        refer to
        https://bioconductor.org/packages/release/bioc/manuals/DESeq/man/DESeq.pdf

    deseq_sharing_mode: str
        :term:`PARAMS`
        determines which dispersion value is saved for each gene
        refer to
        https://bioconductor.org/packages/release/bioc/manuals/DESeq/man/DESeq.pdf

    tags_filter_min_counts_per_row: int
        :term:`PARAMS`
        minimum number of total counts per row to pass filter for analysis

    tags_filter_min_counts_per_sample: int
        :term:`PARAMS`
        minimum number of counts per sample to pass filter for analysis

    tags_filter_percentile_rowsums: int
        :term:`PARAMS`
        remove n% of windows with lowest counts

    outfile:
        filename for deseq results in :term: `tsv` format.
    '''
    design_file, count_file = infiles

    track = P.snip(outfile, ".tsv.gz")

    statement = '''python %(scriptsdir)s/runExpression.py
    --method=deseq
    --tags-tsv-file=%(count_file)s
    --design-tsv-file=%(design_file)s
    --output-filename-pattern=%(track)s.
    --outfile=%(outfile)s
    --fdr=%(deseq_fdr)f
    --deseq-fit-type=%(deseq_fit_type)s
    --deseq-dispersion-method=%(deseq_dispersion_method)s
    --deseq-sharing-mode=%(deseq_sharing_mode)s
    --filter-min-counts-per-row=%(tags_filter_min_counts_per_row)i
    --filter-min-counts-per-sample=%(tags_filter_min_counts_per_sample)i
    --filter-percentile-rowsums=%(tags_filter_percentile_rowsums)i
    > %(outfile)s.log '''

    P.run()


@transform(runDESeq, suffix(".tsv.gz"), "_deseq.load")
def loadDESeq(infile, outfile):
    '''
    Load differential expression results generated by Deseq into database
    table named <track>_gene_diff, where track is the prefix of the deseq
    output file.

    Parameters
    ----------
    infile: str
        output file in :term:`tsv` format from deseq analysis
    outfile: str
        .load database load logfile
    '''
    # add gene level follow convention "<level>_diff"
    P.load(infile,
           outfile,
           tablename=P.toTable(outfile) + "_gene_diff",
           options="--allow-empty-file --add-index=test_id")


@P.add_doc(PipelineRnaseq.buildExpressionStats)
@follows(loadGeneSetGeneInformation)
@merge(loadDESeq, "deseq_stats.tsv")
def buildDESeqStats(infiles, outfile):
    '''
    Parameters
    ----------
    infiles: list
        list of filenames for files containing deseq results formatted into
        :term:`tsv` files

    outfile: str
        file to write compiled deseq results
    '''
    PipelineRnaseq.buildExpressionStats(
        connect(),
        outfile,
        tablenames=[P.toTable(x) + "_gene_diff" for x in infiles],
        outdir=os.path.dirname(infiles[0]))


@transform(buildDESeqStats,
           suffix(".tsv"),
           ".load")
def loadDESeqStats(infile, outfile):
    '''
    Loads compiled deseq stats into a database table - deseq_stats

    Parameters
    ----------
    infile: str
        term:`tsv` file containing deseq stats
    outfile: str
        .load logfile for database load
    '''
    P.load(infile, outfile)


@follows(counting, mkdir("edger.dir"))
@product("design*.tsv",
         formatter("(.*).tsv$"),
         (aggregateGeneLevelReadCounts,
          aggregateFeatureCounts),
         formatter("(.*).tsv.gz$"),
         "edger.dir/{basename[0][0]}.{basename[1][0]}.gz")
def runEdgeR(infiles, outfile):
    '''Perform differential expression analysis using edger.

    Parameters
    ----------
    infiles: list
        list of input filenames

    infiles[0]: str
        Filename with experimental design in :term:`tsv` format

    infiles[1]: str
        filename of file containing tag counts in :term:`tsv` format

    edger_fdr: float
        :term:`PARAMS`
        minimum acceptable fdr for edger

    tags_filter_min_counts_per_row: int
        :term:`PARAMS`
        minimum number of total counts per row to pass filter for analysis

    tags_filter_min_counts_per_sample: int
        :term:`PARAMS`
        minimum number of counts per sample to pass filter for analysis

    tags_filter_percentile_rowsums: int
        :term:`PARAMS`
        remove n% of windows with lowest counts

    outfile:
        filename for edger results in :term: `tsv` format
    '''

    design_file, count_file = infiles
    track = P.snip(outfile, ".tsv.gz")

    statement = '''python %(scriptsdir)s/runExpression.py
    --method=edger
    --tags-tsv-file=%(count_file)s
    --design-tsv-file=%(design_file)s
    --output-filename-pattern=%(track)s.
    --outfile=%(outfile)s
    --fdr=%(edger_fdr)f
    --filter-min-counts-per-row=%(tags_filter_min_counts_per_row)i
    --filter-min-counts-per-sample=%(tags_filter_min_counts_per_sample)i
    --filter-percentile-rowsums=%(tags_filter_percentile_rowsums)i
    > %(outfile)s.log '''

    P.run()


@transform(runEdgeR, suffix(".tsv.gz"), "_edger.load")
def loadEdgeR(infile, outfile):
    '''
    Load differential expression results generated by EdgeR into database
    table named <track>_gene_diff, where track is the prefix of the deseq
    output file.

    Parameters
    ----------
    infile: str
        output file in :term:`tsv` format from edgeR analysis
    outfile: str
        .load database load logfile
    '''
    # add gene level follow convention "<level>_diff"
    P.load(infile,
           outfile,
           tablename=P.toTable(outfile) + "_gene_diff",
           options="--allow-empty-file --add-index=test_id")


@P.add_doc(PipelineRnaseq.buildExpressionStats)
@follows(loadGeneSetGeneInformation)
@merge(loadEdgeR, "edger_stats.tsv")
def buildEdgeRStats(infiles, outfile):
    '''
    Parameters
    ----------
    infiles: list
        list of filenames for files containing edgeR results formatted into
        :term:`tsv` files

    outfile: str
        file to write compiled edgeR results
    '''
    PipelineRnaseq.buildExpressionStats(
        connect(),
        outfile,
        tablenames=[P.toTable(x) + "_gene_diff" for x in infiles],
        outdir=os.path.dirname(infiles[0]))


@transform(buildEdgeRStats,
           suffix(".tsv"),
           ".load")
def loadEdgeRStats(infile, outfile):
    '''Loads compiled EdgeR stats into a database table - edger_stats

    Parameters
    ----------
    infile: str
        term:`tsv` file containing EdgeR stats
    outfile: str
        .load logfile for database load
    '''
    P.load(infile, outfile)


###############################################################################
# Run DESeq2
###############################################################################


@follows(mkdir("deseq2.dir"), counting)
@product("design*.tsv",
         formatter("(.*).tsv$"),
         # (aggregateGeneLevelReadCounts,
         aggregateFeatureCounts,
         formatter("(.*).tsv.gz$"),
         "deseq2.dir/{basename[0][0]}.{basename[1][0]}.gz")
def runDESeq2(infiles, outfile):
    '''Perform differential expression analysis using Deseq2.

    Parameters
    ----------
    infiles: list
        list of input filenames

    infiles[0]: str
        Filename with experimental design in :term:`tsv` format

    infiles[1]: str
        filename of file containing tag counts in :term:`tsv` format

    deseq2_model: str
        :term:`PARAMS`
        model to pass to deseq2, see
        https://bioconductor.org/packages/release/bioc/html/DESeq2.html

    deseq2_contrasts: str
        :term:`PARAMS`
        contrasts to return in pairwise tests in deseq2, see
        https://bioconductor.org/packages/release/bioc/html/DESeq2.html

    tags_filter_min_counts_per_row: int
        :term:`PARAMS`
        minimum number of total counts per row to pass filter for analysis

    tags_filter_min_counts_per_sample: int
        :term:`PARAMS`
        minimum number of counts per sample to pass filter for analysis

    deseq2_filter_percentile_rowsums: int
        :term:`PARAMS`
       remove n% of windows with lowest counts

    outfile:
        filename for deseq results in :term: `tsv` format.
    '''
    design_file, count_file = infiles
    track = P.snip(outfile, ".tsv.gz")

    statement = (
        "python %(scriptsdir)s/runExpression.py"
        " --method=deseq2"
        " --outfile=%(outfile)s"
        " --output-filename-pattern=%(track)s_"
        " --fdr=%(deseq2_fdr)f"
        " --tags-tsv-file=%(count_file)s"
        " --design-tsv-file=%(design_file)s"
        " --deseq2-design-formula=%(deseq2_model)s"
        " --deseq2-contrasts=%(deseq2_contrasts)s"
        " --filter-min-counts-per-row=%(tags_filter_min_counts_per_row)i"
        " --filter-min-counts-per-sample=%(tags_filter_min_counts_per_sample)i"
        " --filter-percentile-rowsums=%(deseq2_filter_percentile_rowsums)i"
        " > %(outfile)s.log")
    P.run()


@transform(runDESeq2, suffix(".tsv.gz"), "_deseq2.load")
def loadDESeq2(infile, outfile):
    """
    Generate globally adjusted pvalue for all contrasts in a design.
    To avoid confusion, drop the DESeq2 generated padj, which is for
    single contrast.  Load table NB. Empty pvalues are due to DESeq2's
    default outlier detection

    Load differential expression results generated by Deseq into database
    table named <track>_gene_diff, where track is the prefix of the deseq
    output file.

    Parameters
    ----------
    infile: str
        output file in :term:`tsv` format from deseq2 analysis
    outfile: str
        .load database load logfile
    """
    # get R p.adjust
    rstats = importr("stats")

    # Read dataframe, extract pvalues, perform global padjust
    df = pandas.read_table(infile, index_col=0, compression="gzip")
    padj = ro.FloatVector(df["pvalue"].tolist())
    padj = rstats.p_adjust(padj, method="BH")
    # padj = rpyn.ri2numpy(padj)
    assert isinstance(padj, numpy.ndarray), \
        "Script assumes pipeline imports module calling numpy2ri.activate()"

    # drop DESeq adjusted pvalues, add instead globally adjusted pvalues
    df.drop("padj", axis=1, inplace=True)
    df["padj_global"] = padj

    # load table containing adjusted pvalues
    tmpf = P.getTempFilename("/ifs/scratch")
    df.to_csv(tmpf, sep="\t")
    P.load(tmpf,
           outfile,
           tablename=P.toTable(outfile) + "_gene_diff",
           options="--add-index=gene_id")
    os.unlink(tmpf)


@follows(mkdir("cuffdiff.dir"), buildMaskGtf)
@product("design*.tsv",
         formatter(".+/(?P<design>.*).tsv$"),
         "*.gtf.gz",
         formatter(".+/(?P<geneset>.*).gtf.gz$"),
         add_inputs("*.bam"),
         r"cuffdiff.dir/{design[0][0]}.{geneset[1][0]}.fpkm.tsv.gz")
def runCuffdiff(infiles, outfile):
    ''' Runs cuffdiff to perform differential expression analysis.

    Parameters
    ----------
    infiles: list
        list of filenames of input files
    infiles[0]: list
        list of filenames
    infiles[0][0]: str
        Filename with experimental design in :term:`tsv` format
    infiles[0][1]: str
        Filename with geneset of interest in :term:`gtf format
    cuffdiff_include_mask: bool
        :term:`PARAMS` if true, use mask file to exclude
        highly expressed genes such as rRNA
    cuffdiff_options: str
        :term:`PARAMS`
        options to pass on to cuffdiff
    cuffdiff_threads: int
        :term:`PARAMS`
         number of threads to use when running cuffdiff
    cuffdiff_memory: str
        :term:`PARAMS`
         memory to reserve for cuffdiff
    cuffdiff_fdr: float
        :term:`PARAMS`
    outfile: str
        Output filename to write FPKM counts.
        The output is :term:`tsv` formatted.
    '''
    design_file, geneset_file = infiles[0]
    bamfiles = infiles[1:]

    if PARAMS["cuffdiff_include_mask"]:
        mask_file = os.path.abspath("geneset_mask.gtf")
    else:
        mask_file = None

    options = PARAMS["cuffdiff_options"] + \
        " --library-type %s" % PARAMS["cufflinks_library_type"]

    PipelineRnaseq.runCuffdiff(bamfiles,
                               design_file,
                               geneset_file,
                               outfile,
                               job_threads=PARAMS.get("cuffdiff_threads", 4),
                               job_memory=PARAMS.get("cuffdiff_memory", "4G"),
                               cuffdiff_options=options,
                               fdr=PARAMS["cuffdiff_fdr"],
                               mask_file=mask_file)


@P.add_doc(PipelineRnaseq.loadCuffdiff)
@transform(runCuffdiff,
           suffix(".tsv.gz"),
           "_cuffdiff.load")
def loadCuffdiff(infile, outfile):
    '''

    Parameters
    ----------
    infile: str
        filename of :term:`tsv` formatted file containing FPKM counts
        generated using cuffdiff
    outfile: str
        .load file containing log for database load

    see PipelineRnaSeq loadCuffdiff module for further details
    '''
    PipelineRnaseq.loadCuffdiff(connect(), infile, outfile)


@follows(mkdir(os.path.join(PARAMS["exportdir"], "cuffdiff")))
@transform(loadCuffdiff,
           suffix(".load"),
           ".plots")
def buildCuffdiffPlots(infile, outfile):
    '''
    Creates plots  of cufflinks results showing fold change against
    expression level

    Plots are created in the <exportdir>/cuffdiff directory.

    Plots are:

    <geneset>_<method>_<level>_<track1>_vs_<track2>_significance.png

    Parameters
    ----------
    infile: str
        .load filename from loading data to the cuffdiff database tables

    outfile: str
        filename of .plots logfile for plotting
    '''
    ###########################################
    ###########################################
    # create diagnostic plots
    ###########################################
    outdir = os.path.join(PARAMS["exportdir"], "cuffdiff")

    dbhandle = sqlite3.connect(PARAMS["database_name"])

    prefix = P.snip(infile, ".load")

    geneset, method = prefix.split("_")

    for level in CUFFDIFF_LEVELS:
        tablename_diff = prefix + "_%s_diff" % level
        tablename_levels = prefix + "_%s_levels" % level

        # note that the ordering of EXPERIMENTS and the _diff table
        # needs to be the same as only one triangle is stored of the
        # pairwise results.  do not plot "undefined" lfold values
        # (where treatment_mean or control_mean = 0) do not plot lfold
        # values where the confidence bounds contain 0.
        for track1, track2 in itertools.combinations(EXPERIMENTS, 2):
            statement = """
            SELECT CASE WHEN d.treatment_mean < d.control_mean
            THEN d.treatment_mean
            ELSE d.control_mean END,
            d.l2fold, d.significant
            FROM %(tablename_diff)s AS d
            WHERE treatment_name = '%(track1)s' AND
            control_name = '%(track2)s' AND
            status = 'OK' AND
            treatment_mean > 0 AND
            control_mean > 0
            """ % locals()

            data = zip(*Database.executewait(dbhandle, statement))

            pngfile = ("%(outdir)s/%(geneset)s_%(method)s_"
                       "%(level)s_%(track1)s_vs_%(track2)s_"
                       "significance.png") % locals()

            # ian: Bug fix: moved R.png to after data check so that no
            #     plot is started if there is no data this was leading
            #     to R falling over from too many open devices

            if len(data) == 0:
                E.warn("no plot for %s - %s -%s vs %s" %
                       (pngfile, level, track1, track2))
                continue

            R.png(pngfile)
            R.plot(ro.FloatVector(data[0]),
                   ro.FloatVector(data[1]),
                   xlab='min(FPKM)',
                   ylab='log2fold',
                   log="x", pch=20, cex=.1,
                   col=R.ifelse(ro.IntVector(data[2]), "red", "black"))

            R['dev.off']()

    P.touch(outfile)


@P.add_doc(PipelineRnaseq.buildExpressionStats)
@follows(loadGeneSetGeneInformation)
@merge(loadCuffdiff,
       "cuffdiff_stats.tsv")
def buildCuffdiffStats(infiles, outfile):
    '''
    Parameters
    ----------
    infiles: list
        list of output files from different levels of cuffdiff analysis
        (gene, isoform, tss etc.)
    outfile:
        :term:`tsv` file containing complied cuffdiff results
    '''
    PipelineRnaseq.buildExpressionStats(
        connect(),
        outfile,
        tablenames=[P.toTable(x) + "_gene_diff" for x in infiles],
        outdir=os.path.dirname(infiles[0]))


@transform(buildCuffdiffStats,
           suffix(".tsv"),
           ".load")
def loadCuffdiffStats(infile, outfile):
    '''Loads a table - cuffdiff_stats - into a database containing cuffdiff
    statistics

    Parameters
    ----------
    infile:
        :term:`tsv` filename containing compiled cuffdiff statistics
    outfile:
        .load logfile for database load
    '''
    P.load(infile, outfile)


@follows(loadCufflinks,
         loadCufflinksFPKM,
         loadGeneLevelReadCounts)
def expression():
    ''' collect outputs from cufflinks'''
    pass


mapToTargets = {'cuffdiff': loadCuffdiffStats,
                'deseq': loadDESeqStats,
                'edger': loadEdgeRStats,
                'deseq2': runDESeq2}

TARGETS_DIFFEXPRESSION = [mapToTargets[x] for x in
                          P.asList(PARAMS["methods"])]


@follows(*TARGETS_DIFFEXPRESSION)
def diff_expression():
    '''collect outputs from "feature counts", "gtf2table.py", "cuffdiff", 
    "DESeq" and "EdgeR"'''
    pass


@follows(diff_expression)
@merge("*_stats.tsv", "de_stats.load")
def loadDEStats(infiles, outfile):
    '''load DE stats into table. 

    concatenates and loads `<track>_stats.tsv` files into database table named
    `de_stats` to show overall summary of DE results.

    Parameters
    ----------

    infiles : list
        list of `<track>_stats.tsv files`
    outfile : string
        `de_stats.load` filename '''
    P.concatenateAndLoad(infiles, outfile,
                         missing_value=0,
                         regex_filename="(.*)_stats.tsv")


@follows(mkdir("tagplots.dir"))
@product("design*.tsv",
         formatter("(.*).tsv$"),
         (aggregateGeneLevelReadCounts,
          aggregateFeatureCounts),
         formatter("(.*).tsv.gz$"),
         "tagplots.dir/{basename[0][0]}.{basename[1][0]}.log")
def plotTagStats(infiles, outfile):
    '''plot of tag counts using runExpression.py .

    plot stats from "feature counts" and "gtf2table.py" :term:`tsv` files

    plots generated in `tagplots.dir` 

    Parameters
    ----------

    infiles : list 
        list of filenames of design files and list of filenames of :term:`tsv.gz'
        files from aggregateGeneLevelReadCounts or aggregateFeatureCounts 
    outfile : string
        filename for naming of several output files in format
        <design>.<geneset>.<countmethod>.log These include:
        * `outfile.tsv.log` - log file
        * `outfile.log.boxplots.png` - boxplot of value vs samples
        * `outfile.log.densities.png - desity plot of density vs value for each sample
'''
    design_file, counts_file = infiles

    statement = '''
    python %(scriptsdir)s/runExpression.py
    --tags-tsv-file=%(counts_file)s
    --design-tsv-file=%(design_file)s
    --method=plottagstats
    --output-filename-pattern=%(outfile)s
    > %(outfile)s
    '''
    P.run()


mapToQCTargets = {'cuffdiff': runCuffdiff,
                  'deseq': runDESeq,
                  'edger': runEdgeR,
                  'deseq2': None,
                  }
QCTARGETS = [mapToQCTargets[x] for x in P.asList(PARAMS["methods"])]


@transform(QCTARGETS,
           suffix(".tsv.gz"),
           ".plots")
def plotDETagStats(infile, outfile):
    '''plot differential expression stats using `runExpression.py`

    Takes :Term:`tsv` files output from EdgeR, DeSeq and cuffdiff and
    uses `runExpression.py` to produce density plots and box plots of
    differential expression in `edger.dir`, `deseq.dir` and
    `cuffdif.dir` directories

    Parameters
    ----------
    infile : string
        filename `<track>.tsv.gz` :term:`tsv` file

    outfile : string
        filename <design>.<geneset>.<genecounts/featurecounts> used to name
        several output files for each DE program:
        * outfile.densities_tags_control.png - denisty plot
        * outfile.densities_tags_treatment.png - denisty plot
        * outfile.boxplot_tags_control.png - boxplot
        * outfile.boxplot_tags_treatment.png - boxplot
        * outfile.plot - log file for plots

    '''

    job_memory = "8G"

    statement = '''
    python %(scriptsdir)s/runExpression.py
    --result-tsv-file=%(infile)s
    --method=plotdetagstats
    --output-filename-pattern=%(outfile)s
    > %(outfile)s
    '''
    P.run()


@follows(plotTagStats,
         plotDETagStats,
         loadTagCountSummary,
         loadDEStats)
def qc():
    ''' collects all DE related tasks'''
    pass


@follows(expression, diff_expression, counting, qc)
def full():
    ''' collects DE tasks and cufflinks transcript build'''
    pass


@follows(mkdir("report"))
def build_report():
    '''build report from scratch.'''

    E.info("starting documentation build process from scratch")
    P.run_report(clean=True)


@follows(mkdir("report"))
def update_report():
    '''update report.'''

    E.info("updating documentation")
    P.run_report(clean=False)


@follows(update_report)
def publish():
    '''publish files.'''
    # publish web pages
    P.publish_report()


if __name__ == "__main__":
    sys.exit(P.main(sys.argv))
