"""=====================
Read mapping pipeline
=====================

:Author: Andreas Heger
:Release: $Id$
:Date: |today|
:Tags: Python

The read mapping pipeline imports unmapped reads from one or more
NGS experiments and maps reads against a reference genome.

This pipeline works on a single genome.

Overview
========

The pipeline implements various mappers and QC plots. It can be used for

* Mapping against a genome
* Mapping RNASEQ data against a genome
* Mapping against a transcriptome

Principal targets
-----------------

mapping
    perform all mappings

qc
    perform all QC steps

full
    compute all mappings and QC

Optional targets
----------------

merge
    merge mapped :term:`bam` formatted files, for example if reads
    from different lanes were mapped separately. After merging, the
    ``qc`` target can be run again to get qc stats for the merged
    :term:`bam` formatted files.


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

Reads are imported by placing files are linking to files in the
:term:`working directory`.

The default file format assumes the following convention:

   filename.<suffix>

The ``suffix`` determines the file type. The following suffixes/file
types are possible:

sra
   Short-Read Archive format. Reads will be extracted using the
   :file:`fastq-dump` tool.

fastq.gz
   Single-end reads in fastq format.

fastq.1.gz, fastq2.2.gz
   Paired-end reads in fastq format. The two fastq files must be
   sorted by read-pair.

.. note::

   Quality scores need to be of the same scale for all input
   files. Thus it might be difficult to mix different formats.

Optional inputs
+++++++++++++++

Requirements
-------------

The pipeline requires the results from
:doc:`pipeline_annotations`. Set the configuration variable
:py:data:`annotations_database` and :py:data:`annotations_dir`.

On top of the default CGAT setup, the pipeline requires the following
software to be in the path:

+---------+------------+------------------------------------------------+
|*Program*|*Version*   |*Purpose*                                       |
+---------+------------+------------------------------------------------+
|bowtie_  |>=0.12.7    |read mapping                                    |
+---------+------------+------------------------------------------------+
|tophat_  |>=1.4.0     |read mapping                                    |
+---------+------------+------------------------------------------------+
|gsnap_   |>=2012.07.20|read mapping                                    |
+---------+------------+------------------------------------------------+
|samtools |>=0.1.16    |bam/sam files                                   |
+---------+------------+------------------------------------------------+
|bedtools |            |working with intervals                          |
+---------+------------+------------------------------------------------+
|sra-tools|            |extracting reads from .sra files                |
+---------+------------+------------------------------------------------+
|picard   |>=1.42      |bam/sam files. The .jar files need to be in your|
|         |            | CLASSPATH environment variable.                |
+---------+------------+------------------------------------------------+
|star_    |>=2.2.0c    |read mapping                                    |
+---------+------------+------------------------------------------------+
|bamstats_|>=1.22      |from CGR, Liverpool                             |
+---------+------------+------------------------------------------------+
|butter   |>=0.3.2     |read mapping                                    |
+---------+------------+------------------------------------------------+
|hisat    |>0.1.5      |read mapping                                    |
+---------+------------+------------------------------------------------+

Merging bam files
-----------------

The pipeline has the ability to merge data post-mapping. This is
useful if data have been split over several lanes and have been
provide as separate fastq files.

To enable merging, set regular expression for the input and output in
the [merge] section of the configuration file.

Pipeline output
===============

The major output is in the database file :file:`csvdb`.

Example
=======

Example data is available at
http://www.cgat.org/~andreas/sample_data/pipeline_mapping.tgz.  To run
the example, simply unpack and untar::

   wget http://www.cgat.org/~andreas/sample_data/pipeline_mapping.tgz
   tar -xvzf pipeline_mapping.tgz
   cd pipeline_mapping
   python <srcdir>/pipeline_mapping.py make full

.. note::
   For the pipeline to run, install the :doc:`pipeline_annotations` as well.

Glossary
========

.. glossary::

   tophat
      tophat_ - a read mapper to detect splice-junctions

   hisat
     hisat_ - a read mapper for RNASEQ data (basis for tophat3)

   bowtie
      bowtie_ - a read mapper

   star
      star_ - a read mapper for RNASEQ data

   bismark
      bismark_ - a read mapper for RRBS data

   butter
      butter_ - a read mapper for small RNA data (bowtie wrapper)

.. _tophat: http://tophat.cbcb.umd.edu/
.. _bowtie: http://bowtie-bio.sourceforge.net/index.shtml
.. _gsnap: http://research-pub.gene.com/gmap/
.. _bamstats: http://www.agf.liv.ac.uk/454/sabkea/samStats_13-01-2011
.. _star: http://code.google.com/p/rna-star/
.. _bismark: http://www.bioinformatics.babraham.ac.uk/projects/bismark/
.. _butter: https://github.com/MikeAxtell/butter
.. _hisat: http://ccb.jhu.edu/software/hisat/manual.shtml

Code
====

"""

# load modules
from ruffus import *

import sys
import os
import re
import glob
import sqlite3
import collections

import CGAT.Experiment as E
import CGATPipelines.Pipeline as P
import CGAT.GTF as GTF
import CGAT.IOTools as IOTools
import CGAT.BamTools as BamTools
import CGATPipelines.PipelineGeneset as PipelineGeneset
import CGATPipelines.PipelineMapping as PipelineMapping
import CGATPipelines.PipelineMappingQC as PipelineMappingQC
import CGATPipelines.PipelineWindows as PipelineWindows

# Pipeline configuration
P.getParameters(
    ["%s/pipeline.ini" % os.path.splitext(__file__)[0],
     "../pipeline.ini",
     "pipeline.ini"],
    defaults={
        'paired_end': False})

PARAMS = P.PARAMS

# Add parameters from the annotation pipeline, but
# only the interface
PARAMS.update(P.peekParameters(
    PARAMS["annotations_dir"],
    "pipeline_annotations.py",
    prefix="annotations_",
    update_interface=True,
    restrict_interface=True))

PipelineGeneset.PARAMS = PARAMS
PipelineMappingQC.PARAMS = PARAMS

# Helper functions mapping tracks to conditions, etc
# determine the location of the input files (reads).
try:
    PARAMS["input"]
except NameError:
    DATADIR = "."
else:
    if PARAMS["input"] == 0:
        DATADIR = "."
    elif PARAMS["input"] == 1:
        DATADIR = "data.dir"
    else:
        DATADIR = PARAMS["input"]  # not recommended practise.


# Global flags
MAPPERS = P.asList(PARAMS["mappers"])
SPLICED_MAPPING = ("tophat" in MAPPERS or
                   "gsnap" in MAPPERS or
                   "star" in MAPPERS or
                   "tophat2" in MAPPERS or
                   "transcriptome" in MAPPERS or
                   "hisat" in MAPPERS)


def connect():
    '''connect to database.

    This method also attaches to helper databases.
    '''

    dbh = sqlite3.connect(PARAMS["database_name"])

    if not os.path.exists(PARAMS["annotations_database"]):
        raise ValueError(
            "can't find database '%s'" %
            PARAMS["annotations_database"])

    statement = '''ATTACH DATABASE '%s' as annotations''' % \
                (PARAMS["annotations_database"])

    cc = dbh.cursor()
    cc.execute(statement)
    cc.close()

    return dbh


@active_if(SPLICED_MAPPING)
@follows(mkdir("geneset.dir"))
@merge(PARAMS["annotations_interface_geneset_all_gtf"],
       "geneset.dir/reference.gtf.gz")
def buildReferenceGeneSet(infile, outfile):
    '''sanitize ENSEMBL transcripts file for cufflinks analysis.

    Merge exons separated by small introns (< 5bp).

    Removes unwanted contigs according to configuration
    value ``geneset_remove_contigs``.

    Removes transcripts overlapping ribosomal genes if
    ``geneset_remove_repetitive_rna`` is set. Protein coding
    transcripts are not removed.

    Transcripts will be ignored that
       * have very long introns (max_intron_size) (otherwise,
         cufflinks complains)
       * are located on contigs to be ignored (usually: chrM, _random, ...)

    The result is run through cuffdiff in order to add the p_id and
    tss_id tags required by cuffdiff.

    This will only keep sources of the type 'exon'. It will also remove
    any transcripts not in the reference genome.

    Cuffdiff requires overlapping genes to have different tss_id tags.

    This geneset is the source for most other genesets in the pipeline.

    '''
    tmp_mergedfiltered = P.getTempFilename(".")

    if "geneset_remove_repetetive_rna" in PARAMS:
        rna_file = PARAMS["annotations_interface_rna_gff"]
    else:
        rna_file = None

    gene_ids = PipelineMapping.mergeAndFilterGTF(
        infile,
        tmp_mergedfiltered,
        "%s.removed.gz" % outfile,
        genome=os.path.join(PARAMS["genome_dir"], PARAMS["genome"]),
        max_intron_size=PARAMS["max_intron_size"],
        remove_contigs=PARAMS["geneset_remove_contigs"],
        rna_file=rna_file)

    # Add tss_id and p_id
    PipelineMapping.resetGTFAttributes(
        infile=tmp_mergedfiltered,
        genome=os.path.join(PARAMS["genome_dir"], PARAMS["genome"]),
        gene_ids=gene_ids,
        outfile=outfile)

    os.unlink(tmp_mergedfiltered)


@active_if(SPLICED_MAPPING)
@originate("protein_coding_gene_ids.tsv")
def identifyProteinCodingGenes(outfile):
    """output a list of proteing coding gene identifiers."""

    dbh = connect()

    table = os.path.basename(PARAMS["annotations_interface_table_gene_info"])

    select = dbh.execute("""SELECT DISTINCT gene_id
    FROM annotations.%(table)s
    WHERE gene_biotype = 'protein_coding'""" % locals())

    with IOTools.openFile(outfile, "w") as outf:
        outf.write("gene_id\n")
        outf.write("\n".join((x[0] for x in select)) + "\n")


@active_if(SPLICED_MAPPING)
@transform(buildReferenceGeneSet,
           suffix("reference.gtf.gz"),
           add_inputs(identifyProteinCodingGenes),
           "refcoding.gtf.gz")
def buildCodingGeneSet(infiles, outfile):
    '''build a gene set with only protein coding transcripts.

    Genes are no longer selected via their gene biotype in the GTF file.

    Genes are now identified from the annotation database table and then
    provided in a tsv file to gtf2gtf.py

    Note that this set will contain all transcripts of protein
    coding genes, including processed transcripts.

    This set includes UTR and CDS.

    '''

    infile, genes_tsv = infiles

    statement = '''
    zcat %(infile)s
    | python %(scriptsdir)s/gtf2gtf.py
    --method=filter
    --filter-method=gene
    --map-tsv-file=%(genes_tsv)s
    --log=%(outfile)s.log
    | gzip
    > %(outfile)s
    '''
    P.run()

#########################################################################
#########################################################################
#########################################################################


@active_if(SPLICED_MAPPING)
@follows(mkdir("geneset.dir"))
@transform(PARAMS["annotations_interface_geneset_flat_gtf"],
           regex(".*"),
           add_inputs(identifyProteinCodingGenes),
           "geneset.dir/introns.gtf.gz")
def buildIntronGeneModels(infiles, outfile):
    '''build protein-coding intron-transcipts.

    Intron-transcripts are the reverse complement of transcripts.

    Only protein coding genes are taken.

    10 bp are truncated on either end of an intron and need
    to have a minimum length of 100.

    Introns from nested genes might overlap, but all exons
    are removed.
    '''

    filename_exons = PARAMS["annotations_interface_geneset_exons_gtf"]

    infile, genes_tsv = infiles

    statement = '''
    zcat %(infile)s
    | python %(scriptsdir)s/gtf2gtf.py
    --method=filter
    --map-tsv-file=%(genes_tsv)s
    --log=%(outfile)s.log
    | python %(scriptsdir)s/gtf2gtf.py
    --method=sort
    --sort-order=gene
    | python %(scriptsdir)s/gtf2gtf.py
    --method=exons2introns
    --intron-min-length=100
    --intron-border=10
    --log=%(outfile)s.log
    | python %(scriptsdir)s/gff2gff.py
    --method=crop
    --crop-gff-file=%(filename_exons)s
    --log=%(outfile)s.log
    | python %(scriptsdir)s/gtf2gtf.py
    --method=set-transcript-to-gene
    --log=%(outfile)s.log
    | awk -v OFS="\\t" -v FS="\\t" '{$3="exon"; print}'
    | gzip
    > %(outfile)s
    '''
    P.run()


@active_if(SPLICED_MAPPING)
@transform(buildCodingGeneSet,
           suffix(".gtf.gz"),
           "_transcript2gene.load")
def loadGeneInformation(infile, outfile):
    PipelineGeneset.loadTranscript2Gene(infile, outfile)


@active_if(SPLICED_MAPPING)
@follows(mkdir("geneset.dir"))
@merge(PARAMS["annotations_interface_geneset_all_gtf"],
       "geneset.dir/coding_exons.gtf.gz")
def buildCodingExons(infile, outfile):
    '''compile set of protein coding exons.

    This set is used for splice-site validation
    '''

    statement = '''
    zcat %(infile)s
    | awk '$3 == "CDS"'
    | python %(scriptsdir)s/gtf2gtf.py
    --method=filter
    --filter-method=proteincoding
    --log=%(outfile)s.log
    | awk -v OFS="\\t" -v FS="\\t" '{$3="exon"; print}'
    | python %(scriptsdir)s/gtf2gtf.py
    --method=merge-exons
    --log=%(outfile)s.log
    | gzip
    > %(outfile)s
    '''
    P.run()


@active_if(SPLICED_MAPPING)
@transform(buildCodingGeneSet, suffix(".gtf.gz"), ".fa")
def buildReferenceTranscriptome(infile, outfile):
    '''build reference transcriptome.

    The reference transcriptome contains all known protein coding
    transcripts.

    The sequences include both UTR and CDS.

    Builds bowtie indices for tophat/tophat2 if
    required.
    '''
    gtf_file = P.snip(infile, ".gz")

    genome_file = os.path.abspath(
        os.path.join(PARAMS["genome_dir"], PARAMS["genome"] + ".fa"))

    statement = '''
    zcat %(infile)s
    | awk '$3 == "exon"' > %(gtf_file)s;
    gtf_to_fasta %(gtf_file)s %(genome_file)s %(outfile)s;
    checkpoint;
    samtools faidx %(outfile)s
    '''
    P.run()

    dest = P.snip(os.path.abspath(gtf_file), ".gtf") + ".gff"
    if not os.path.exists(dest):
        os.symlink(os.path.abspath(gtf_file), dest)

    prefix = P.snip(outfile, ".fa")

    if 'tophat' in MAPPERS or "transcriptome" in MAPPERS:
        # build raw index
        statement = '''
        bowtie-build -f %(outfile)s %(prefix)s >> %(outfile)s.log 2>&1
        '''
        P.run()

        # build color space index - disabled
        # statement = '''
        # bowtie-build -C -f %(outfile)s %(prefix)s_cs
        # >> %(outfile)s.log 2>&1
        # '''
        # P.run()

    if 'tophat2' in MAPPERS:
        statement = '''
        bowtie2-build -f %(outfile)s %(prefix)s >> %(outfile)s.log 2>&1
        '''
        P.run()

#########################################################################
#########################################################################
#########################################################################


@active_if(SPLICED_MAPPING)
@transform(buildCodingGeneSet, suffix(".gtf.gz"), ".junctions")
def buildJunctions(infile, outfile):
    '''build file with splice junctions from gtf file.

    A junctions file is a better option than supplying a GTF
    file, as parsing the latter often fails. See:

    http://seqanswers.com/forums/showthread.php?t=7563

    '''

    outf = IOTools.openFile(outfile, "w")
    njunctions = 0
    for gffs in GTF.transcript_iterator(
            GTF.iterator(IOTools.openFile(infile, "r"))):

        gffs.sort(key=lambda x: x.start)
        end = gffs[0].end
        for gff in gffs[1:]:
            # subtract one: these are not open/closed coordinates but
            # the 0-based coordinates
            # of first and last residue that are to be kept (i.e., within the
            # exon).
            outf.write("%s\t%i\t%i\t%s\n" %
                       (gff.contig, end - 1, gff.start, gff.strand))
            end = gff.end
            njunctions += 1

    outf.close()

    if njunctions == 0:
        E.warn('no junctions found in gene set')
        return
    else:
        E.info('found %i junctions before removing duplicates' % njunctions)

    # make unique
    statement = '''mv %(outfile)s %(outfile)s.tmp;
                   cat < %(outfile)s.tmp | sort | uniq > %(outfile)s;
                   rm -f %(outfile)s.tmp; '''
    P.run()


@active_if(SPLICED_MAPPING)
@follows(mkdir("gsnap.dir"))
@merge(PARAMS["annotations_interface_geneset_exons_gtf"],
       "gsnap.dir/splicesites.iit")
def buildGSNAPSpliceSites(infile, outfile):
    '''build file with known splice sites for GSNAP from all exons...
    '''

    outfile = P.snip(outfile, ".iit")
    statement = '''zcat %(infile)s
    | gtf_splicesites | iit_store -o %(outfile)s
    > %(outfile)s.log
    '''

    P.run()

#########################################################################
#########################################################################
#########################################################################
# Read mapping
#########################################################################

SEQUENCESUFFIXES = ("*.fastq.1.gz",
                    "*.fastq.gz",
                    "*.fa.gz",
                    "*.sra",
                    "*.export.txt.gz",
                    "*.csfasta.gz",
                    "*.csfasta.F3.gz",
                    )

SEQUENCEFILES = tuple([os.path.join(DATADIR, suffix_name)
                      for suffix_name in SEQUENCESUFFIXES])

SEQUENCEFILES_REGEX = regex(
    r".*/(\S+).(fastq.1.gz|fastq.gz|fa.gz|sra|csfasta.gz|csfasta.F3.gz|export.txt.gz)")

###################################################################
###################################################################
###################################################################
# load number of reads
###################################################################


@follows(mkdir("nreads.dir"))
@transform(SEQUENCEFILES,
           SEQUENCEFILES_REGEX,
           r"nreads.dir/\1.nreads")
def countReads(infile, outfile):
    '''count number of reads in input files.'''
    m = PipelineMapping.Counter()
    statement = m.build((infile,), outfile)
    P.run()

#########################################################################
#########################################################################
#########################################################################
# Map reads with tophat
#########################################################################


@active_if(SPLICED_MAPPING)
@follows(mkdir("tophat.dir"))
@transform(SEQUENCEFILES,
           SEQUENCEFILES_REGEX,
           add_inputs(buildJunctions, buildReferenceTranscriptome),
           r"tophat.dir/\1.tophat.bam")
def mapReadsWithTophat(infiles, outfile):
    '''map reads from .fastq or .sra files.

    A list with known splice junctions is supplied.

    If tophat fails with an error such as::

       Error: segment-based junction search failed with err =-6
       what():  std::bad_alloc

    it means that it ran out of memory.

    '''
    job_threads = PARAMS["tophat_threads"]

    if "--butterfly-search" in PARAMS["tophat_options"]:
        # for butterfly search - require insane amount of
        # RAM.
        job_memory = "50G"
    else:
        job_memory = PARAMS["tophat_memory"]

    m = PipelineMapping.Tophat(
        executable=P.substituteParameters(**locals())["tophat_executable"],
        strip_sequence=PARAMS["strip_sequence"])
    infile, reffile, transcriptfile = infiles
    tophat_options = PARAMS["tophat_options"] + \
        " --raw-juncs %(reffile)s " % locals()

    # Nick - added the option to map to the reference transcriptome first
    # (built within the pipeline)
    if PARAMS["tophat_include_reference_transcriptome"]:
        prefix = os.path.abspath(P.snip(transcriptfile, ".fa"))
        tophat_options = tophat_options + \
            " --transcriptome-index=%s -n 2" % prefix

    statement = m.build((infile,), outfile)
    P.run()


@active_if(SPLICED_MAPPING)
@follows(mkdir("tophat2.dir"))
@transform(SEQUENCEFILES,
           SEQUENCEFILES_REGEX,
           add_inputs(buildJunctions, buildReferenceTranscriptome),
           r"tophat2.dir/\1.tophat2.bam")
def mapReadsWithTophat2(infiles, outfile):
    '''map reads from .fastq or .sra files.

    A list with known splice junctions is supplied.

    If tophat fails with an error such as::

       Error: segment-based junction search failed with err =-6
       what():  std::bad_alloc

    it means that it ran out of memory.

    '''
    job_threads = PARAMS["tophat2_threads"]

    if "--butterfly-search" in PARAMS["tophat2_options"]:
        # for butterfly search - require insane amount of
        # RAM.
        job_memory = "50G"
    else:
        job_memory = PARAMS["tophat2_memory"]

    m = PipelineMapping.Tophat2(
        executable=P.substituteParameters(**locals())["tophat2_executable"],
        strip_sequence=PARAMS["strip_sequence"])

    infile, reffile, transcriptfile = infiles
    tophat2_options = PARAMS["tophat2_options"] + " --raw-juncs %(reffile)s " % locals()

    # Nick - added the option to map to the reference transcriptome first
    # (built within the pipeline)
    if PARAMS["tophat2_include_reference_transcriptome"]:
        prefix = os.path.abspath(P.snip(transcriptfile, ".fa"))
        tophat2_options = tophat2_options + \
            " --transcriptome-index=%s -n 2" % prefix

    statement = m.build((infile,), outfile)
    P.run()

############################################################
############################################################
############################################################


@active_if(SPLICED_MAPPING)
@follows(mkdir("hisat.dir"))
@transform(SEQUENCEFILES,
           SEQUENCEFILES_REGEX,
           add_inputs(buildJunctions),
           r"hisat.dir/\1.hisat.bam")
def mapReadsWithHisat(infiles, outfile):
    '''map reads from .fastq or .sra files.

    A list with known splice junctions is supplied.

    If hisat fails with an error such as::

       Error: segment-based junction search failed with err =-6
       what():  std::bad_alloc

    it means that it ran out of memory.

    '''
    job_threads = PARAMS["hisat_threads"]
    job_memory = PARAMS["hisat_memory"]

    m = PipelineMapping.Hisat(
        executable=P.substituteParameters(**locals())["hisat_executable"],
        strip_sequence=PARAMS["strip_sequence"],
	strandedness=PARAMS["hisat_library_type"])

    infile, junctions = infiles

    statement = m.build((infile,), outfile)

    P.run()

############################################################
############################################################
############################################################


@active_if(SPLICED_MAPPING)
@merge(mapReadsWithTophat, "tophat_stats.tsv")
def buildTophatStats(infiles, outfile):

    def _select(lines, pattern):
        x = re.compile(pattern)
        for line in lines:
            r = x.search(line)
            if r:
                g = r.groups()
                if len(g) > 1:
                    return g
                else:
                    return g[0]

        raise ValueError("pattern '%s' not found %s" % (pattern, lines))

    outf = IOTools.openFile(outfile, "w")
    outf.write("\t".join(("track",
                          "reads_in",
                          "reads_removed",
                          "reads_out",
                          "junctions_loaded",
                          "junctions_found",
                          "possible_splices")) + "\n")

    for infile in infiles:

        track = P.snip(infile, ".bam")
        indir = infile + ".logs"

        fn = os.path.join(indir, "prep_reads.log")
        lines = open(fn).readlines()
        reads_removed, reads_in = map(
            int, _select(lines, "(\d+) out of (\d+) reads have been filtered out"))
        reads_out = reads_in - reads_removed
        prep_reads_version = _select(lines, "prep_reads (.*)$")

        fn = os.path.join(indir, "reports.log")
        lines = open(fn).readlines()
        tophat_reports_version = _select(lines, "tophat_reports (.*)$")
        junctions_loaded = int(_select(lines, "Loaded (\d+) junctions"))
        junctions_found = int(
            _select(lines, "Found (\d+) junctions from happy spliced reads"))

        fn = os.path.join(indir, "segment_juncs.log")

        if os.path.exists(fn):
            lines = open(fn).readlines()
            if len(lines) > 0:
                segment_juncs_version = _select(lines, "segment_juncs (.*)$")
                possible_splices = int(
                    _select(lines, "Reported (\d+) total potential splices"))
            else:
                segment_juncs_version = "na"
                possible_splices = ""
        else:
            segment_juncs_version = "na"
            possible_splices = ""

        # fix for paired end reads - tophat reports pairs, not reads
        if PARAMS["paired_end"]:
            reads_in *= 2
            reads_out *= 2
            reads_removed *= 2

        outf.write("\t".join(map(str, (
            track,
            reads_in, reads_removed, reads_out,
            junctions_loaded, junctions_found, possible_splices))) + "\n")

    outf.close()


@jobs_limit(PARAMS.get("jobs_limit_db", 1), "db")
@active_if(SPLICED_MAPPING)
@transform(buildTophatStats, suffix(".tsv"), ".load")
def loadTophatStats(infile, outfile):
    P.load(infile, outfile)


@active_if(SPLICED_MAPPING)
@follows(mkdir("gsnap.dir"))
@transform(SEQUENCEFILES,
           SEQUENCEFILES_REGEX,
           add_inputs(buildGSNAPSpliceSites),
           r"gsnap.dir/\1.gsnap.bam")
def mapReadsWithGSNAP(infiles, outfile):
    '''map reads from .fastq or .sra files.

    '''

    infile, infile_splices = infiles

    job_memory = PARAMS["gsnap_memory"]
    job_threads = PARAMS["gsnap_node_threads"]
    gsnap_mapping_genome = PARAMS["gsnap_genome"] or PARAMS["genome"]

    m = PipelineMapping.GSNAP(
        executable=P.substituteParameters(**locals())["gsnap_executable"],
        strip_sequence=PARAMS["strip_sequence"])

    if PARAMS["gsnap_include_known_splice_sites"]:
        gsnap_options = PARAMS["gsnap_options"] + \
            " --use-splicing=%(infile_splices)s " % locals()

    statement = m.build((infile,), outfile)
    P.run()


@active_if(SPLICED_MAPPING)
@follows(mkdir("star.dir"))
@transform(SEQUENCEFILES,
           SEQUENCEFILES_REGEX,
           r"star.dir/\1.star.bam")
def mapReadsWithSTAR(infile, outfile):
    '''map reads from .fastq or .sra files.

    '''

    job_threads = PARAMS["star_threads"]
    job_memory = PARAMS["star_memory"]

    star_mapping_genome = PARAMS["star_genome"] or PARAMS["genome"]

    m = PipelineMapping.STAR(
        executable=P.substituteParameters(**locals())["star_executable"],
        strip_sequence=PARAMS["strip_sequence"])

    statement = m.build((infile,), outfile)
    P.run()


@active_if(SPLICED_MAPPING)
@merge(mapReadsWithSTAR, "star_stats.tsv")
def buildSTARStats(infiles, outfile):
    '''load stats from STAR run.'''

    data = collections.defaultdict(list)
    for infile in infiles:
        fn = infile + ".final.log"
        if not os.path.exists(fn):
            raise ValueError("incomplete run: %s" % infile)

        for line in IOTools.openFile(fn):
            if "|" not in line:
                continue
            header, value = line.split("|")
            header = re.sub("%", "percent", header)
            data[header.strip()].append(value.strip())

    keys = data.keys()
    outf = IOTools.openFile(outfile, "w")
    outf.write("track\t%s\n" % "\t".join(keys))
    for x, infile in enumerate(infiles):
        track = P.snip(os.path.basename(infile), ".bam")
        outf.write("%s\t%s\n" %
                   (track, "\t".join([data[key][x] for key in keys])))
    outf.close()


@jobs_limit(PARAMS.get("jobs_limit_db", 1), "db")
@active_if(SPLICED_MAPPING)
@transform(buildSTARStats, suffix(".tsv"), ".load")
def loadSTARStats(infile, outfile):
    '''load stats from STAR run.'''
    P.load(infile, outfile)


@active_if(SPLICED_MAPPING)
@follows(mkdir("transcriptome.dir"))
@transform(SEQUENCEFILES,
           SEQUENCEFILES_REGEX,
           add_inputs(buildReferenceTranscriptome),
           r"transcriptome.dir/\1.trans.bam")
def mapReadsWithBowtieAgainstTranscriptome(infiles, outfile):
    '''map reads using bowtie against transcriptome data.
    '''

    # Mapping will permit up to one mismatches. This is sufficient
    # as the downstream filter in rnaseq_bams2bam requires the
    # number of mismatches less than the genomic number of mismatches.
    # Change this, if the number of permitted mismatches for the genome
    # increases.

    # Output all valid matches in the best stratum. This will
    # inflate the file sizes due to matches to alternative transcripts
    # but otherwise matches to paralogs will be missed (and such
    # reads would be filtered out).
    job_threads = PARAMS["bowtie_threads"]
    m = PipelineMapping.BowtieTranscripts(
        executable=P.substituteParameters(**locals())["bowtie_executable"],
        strip_sequence=PARAMS["strip_sequence"])
    infile, reffile = infiles
    prefix = P.snip(reffile, ".fa")
    # IMS: moved reporting options to ini
    # bowtie_options = "%s --best --strata -a" % PARAMS["bowtie_transcriptome_options"]
    statement = m.build((infile,), outfile)
    P.run()


@follows(mkdir("bowtie.dir"))
@transform(SEQUENCEFILES,
           SEQUENCEFILES_REGEX,
           add_inputs(
               os.path.join(PARAMS["bowtie_index_dir"],
                            PARAMS["genome"] + ".fa")),
           r"bowtie.dir/\1.bowtie.bam")
def mapReadsWithBowtie(infiles, outfile):
    '''map reads with bowtie. For bowtie2 set executable apppropriately.'''

    job_threads = PARAMS["bowtie_threads"]
    job_memory = PARAMS["bowtie_memory"]

    m = PipelineMapping.Bowtie(
        executable=P.substituteParameters(**locals())["bowtie_executable"],
        tool_options=P.substituteParameters(**locals())["bowtie_options"],
        strip_sequence=PARAMS["strip_sequence"])
    infile, reffile = infiles
    statement = m.build((infile,), outfile)
    P.run()


@follows(mkdir("bowtie2.dir"))
@transform(SEQUENCEFILES,
           SEQUENCEFILES_REGEX,
           add_inputs(
               os.path.join(PARAMS["bowtie_index_dir"],
                            PARAMS["genome"] + ".fa")),
           r"bowtie2.dir/\1.bowtie2.bam")
def mapReadsWithBowtie2(infiles, outfile):
    '''map reads with bowtie. For bowtie2 set executable apppropriately.'''

    job_threads = PARAMS["bowtie2_threads"]
    job_memory = PARAMS["bowtie2_memory"]

    m = PipelineMapping.Bowtie2(
        executable=P.substituteParameters(**locals())["bowtie2_executable"],
        tool_options=P.substituteParameters(**locals())["bowtie2_options"],
        strip_sequence=PARAMS["strip_sequence"])
    infile, reffile = infiles
    statement = m.build((infile,), outfile)
    P.run()


@follows(mkdir("bwa.dir"))
@transform(SEQUENCEFILES,
           SEQUENCEFILES_REGEX,
           r"bwa.dir/\1.bwa.bam")
def mapReadsWithBWA(infile, outfile):
    '''map reads with bwa'''

    job_threads = PARAMS["bwa_threads"]
    job_memory = PARAMS["bwa_memory"]

    if PARAMS["bwa_algorithm"] == "aln":
        m = PipelineMapping.BWA(
            remove_non_unique=PARAMS["remove_non_unique"],
            strip_sequence=PARAMS["strip_sequence"],
            set_nh=PARAMS["bwa_set_nh"])
    elif PARAMS["bwa_algorithm"] == "mem":
        m = PipelineMapping.BWAMEM(
            remove_non_unique=PARAMS["remove_non_unique"],
            strip_sequence=PARAMS["strip_sequence"],
            set_nh=PARAMS["bwa_set_nh"])
    else:
        raise ValueError("bwa algorithm '%s' not known" % algorithm)

    statement = m.build((infile,), outfile)
    P.run()


@follows(mkdir("stampy.dir"))
@transform(SEQUENCEFILES,
           SEQUENCEFILES_REGEX,
           r"stampy.dir/\1.stampy.bam")
def mapReadsWithStampy(infile, outfile):
    '''map reads with stampy'''

    job_threads = PARAMS["stampy_threads"]
    job_memory = PARAMS["stampy_memory"]

    m = PipelineMapping.Stampy(strip_sequence=PARAMS["strip_sequence"])
    statement = m.build((infile,), outfile)
    P.run()

###################################################################
###################################################################
###################################################################
# Map reads with butter
###################################################################


@follows(mkdir("butter.dir"))
@transform(SEQUENCEFILES,
           SEQUENCEFILES_REGEX,
           r"butter.dir/\1.butter.bam")
def mapReadsWithButter(infile, outfile):
    '''map reads with butter'''
    # easier to check whether infiles are paired reads here
    if infile.endswith(".sra"):
        outdir = P.getTempDir()
        f = Sra.sneak(infile, outdir)
        shutil.rmtree(outdir)
        assert len(f) == 1, NotImplementedError('''The sra archive contains
        paired end data,Butter does not support paired end reads''')

    elif infile.endswith(".csfasta.F3.gz") or infile.endswith(".fastq.1.gz"):
        raise NotImplementedError('''infiles are paired end: %(infile)s,
        Butter does not support paired end reads''' % locals())

    job_threads = PARAMS["butter_threads"]
    job_memory = PARAMS["butter_memory"]

    m = PipelineMapping.Butter(
        strip_sequence=PARAMS["strip_sequence"],
        set_nh=PARAMS["butter_set_nh"])

    P.run()

###################################################################
###################################################################
###################################################################
# Create map reads tasks
###################################################################

MAPPINGTARGETS = []
mapToMappingTargets = {'tophat': (mapReadsWithTophat, loadTophatStats),
                       'tophat2': (mapReadsWithTophat2,),
                       'bowtie': (mapReadsWithBowtie,),
                       'bowtie2': (mapReadsWithBowtie2,),
                       'bwa': (mapReadsWithBWA,),
                       'stampy': (mapReadsWithStampy,),
                       'transcriptome':
                       (mapReadsWithBowtieAgainstTranscriptome,),
                       'gsnap': (mapReadsWithGSNAP,),
                       'star': (mapReadsWithSTAR, loadSTARStats),
                       'butter': (mapReadsWithButter,),
                       'hisat': (mapReadsWithHisat,)
                       }

for x in P.asList(PARAMS["mappers"]):
    MAPPINGTARGETS.extend(mapToMappingTargets[x])


@follows(*MAPPINGTARGETS)
def mapping():
    pass


if "merge_pattern_input" in PARAMS and PARAMS["merge_pattern_input"]:
    if "merge_pattern_output" not in PARAMS or \
       not PARAMS["merge_pattern_output"]:
        raise ValueError(
            "no output pattern 'merge_pattern_output' specified")

    @collate(MAPPINGTARGETS,
             regex("%s\.([^.]+).bam" % PARAMS["merge_pattern_input"].strip()),
             # the last expression counts number of groups in pattern_input
             r"%s.\%i.bam" % (PARAMS["merge_pattern_output"].strip(),
                              PARAMS["merge_pattern_input"].count("(") + 1),
             )
    def mergeBAMFiles(infiles, outfile):
        '''merge BAM files from the same experiment.'''
        if len(infiles) == 1:
            E.info(
                "%(outfile)s: only one file for merging - creating "
                "softlink" % locals())
            P.clone(infiles[0], outfile)
            P.clone(infiles[0] + ".bai", outfile + ".bai")
            return

        infiles = " ".join(infiles)
        statement = '''
        samtools merge %(outfile)s %(infiles)s >& %(outfile)s.log;
        checkpoint;
        samtools index %(outfile)s
        '''
        P.run()

    MAPPINGTARGETS = MAPPINGTARGETS + [mergeBAMFiles]

    @collate(countReads,
             regex("%s.nreads" % PARAMS["merge_pattern_input"]),
             r"%s.nreads" % PARAMS["merge_pattern_output"],
             )
    def mergeReadCounts(infiles, outfile):
        '''merge BAM files from the same experiment.'''

        nreads = 0
        for infile in infiles:
            with IOTools.openFile(infile, "r") as inf:
                for line in inf:
                    if not line.startswith("nreads"):
                        continue
                    E.info("%s" % line[:-1])
                    nreads += int(line[:-1].split("\t")[1])

        outf = IOTools.openFile(outfile, "w")
        outf.write("nreads\t%i\n" % nreads)
        outf.close()

else:
    @follows(countReads)
    @transform(SEQUENCEFILES,
               SEQUENCEFILES_REGEX,
               r"nreads.dir/\1.nreads")
    # this decorator for the dummy mergeReadCounts is needed to prevent
    # rerunning of all downstream functions.
    def mergeReadCounts():
        pass

###################################################################
###################################################################
###################################################################
# QC targets
###################################################################

###################################################################
###################################################################
###################################################################
#
# This is not a pipelined task - remove?
#
# @active_if( SPLICED_MAPPING )
# @transform( MAPPINGTARGETS,
#             suffix(".bam" ),
#             ".picard_inserts")
# def buildPicardTranscriptomeInsertSize( infiles, outfile ):
#     '''build alignment stats using picard.

#     Note that picards counts reads but they are in fact alignments.
#     '''
#     infile, reffile = infiles

#     PipelineMappingQC.buildPicardAlignmentStats( infile,
#                                                  outfile,
#                                                  reffile )

############################################################
###########################################################
############################################################


@transform(MAPPINGTARGETS,
           suffix(".bam"),
           add_inputs(os.path.join(PARAMS["genome_dir"],
                                   PARAMS["genome"] + ".fa")),
           ".picard_stats")
def buildPicardStats(infiles, outfile):
    '''build alignment stats using picard.

    Note that picards counts reads but they are in fact alignments.
    '''
    infile, reffile = infiles

    # patch for mapping against transcriptome - switch genomic reference
    # to transcriptomic sequences
    if "transcriptome.dir" in infile:
        reffile = "refcoding.fa"

    PipelineMappingQC.buildPicardAlignmentStats(infile,
                                                outfile,
                                                reffile)


@jobs_limit(PARAMS.get("jobs_limit_db", 1), "db")
@merge(buildPicardStats, "picard_stats.load")
def loadPicardStats(infiles, outfile):
    '''merge alignment stats into single tables.'''
    PipelineMappingQC.loadPicardAlignmentStats(infiles, outfile)


@transform(MAPPINGTARGETS,
           suffix(".bam"),
           ".picard_duplication_metrics")
def buildPicardDuplicationStats(infile, outfile):
    '''Get duplicate stats from picard MarkDuplicates.

    Pair duplication is properly handled, including inter-chromosomal
    cases. SE data is also handled.  These stats also contain a
    histogram that estimates the return from additional sequecing.  No
    marked bam files are retained (/dev/null...)  Note that picards
    counts reads but they are in fact alignments.

    '''
    PipelineMappingQC.buildPicardDuplicationStats(infile, outfile)


@jobs_limit(PARAMS.get("jobs_limit_db", 1), "db")
@merge(buildPicardDuplicationStats, ["picard_duplication_stats.load",
                                     "picard_duplication_histogram.load"])
def loadPicardDuplicationStats(infiles, outfiles):
    '''merge alignment stats into single tables.'''
    # separate load function while testing
    PipelineMappingQC.loadPicardDuplicationStats(infiles, outfiles)


@follows(countReads, mergeReadCounts)
@transform(MAPPINGTARGETS,
           regex("(.*)/(.*)\.(.*).bam"),
           add_inputs(r"nreads.dir/\2.nreads"),
           r"\1/\2.\3.readstats")
def buildBAMStats(infiles, outfile):
    '''count number of reads mapped, duplicates, etc.
    '''

    rna_file = PARAMS["annotations_interface_rna_gff"]

    job_memory = "16G"

    bamfile, readsfile = infiles

    nreads = PipelineMappingQC.getNumReadsFromReadsFile(readsfile)
    track = P.snip(os.path.basename(readsfile),
                   ".nreads")

    # if a fastq file exists, submit for counting
    if os.path.exists(track + ".fastq.gz"):
        fastqfile = track + ".fastq.gz"
    elif os.path.exists(track + ".fastq.1.gz"):
        fastqfile = track + ".fastq.1.gz"
    else:
        fastqfile = None

    if fastqfile is not None:
        fastq_option = "--fastq-file=%s" % fastqfile
    else:
        fastq_option = ""

    statement = '''python
    %(scriptsdir)s/bam2stats.py
         %(fastq_option)s
         --force-output
         --mask-bed-file=%(rna_file)s
         --ignore-masked-reads
         --num-reads=%(nreads)i
         --output-filename-pattern=%(outfile)s.%%s
    < %(bamfile)s
    > %(outfile)s
    '''

    P.run()


@jobs_limit(PARAMS.get("jobs_limit_db", 1), "db")
@merge(buildBAMStats, "bam_stats.load")
def loadBAMStats(infiles, outfile):
    '''import bam statisticis.'''
    PipelineMappingQC.loadBAMStats(infiles, outfile)


@transform(MAPPINGTARGETS,
           suffix(".bam"),
           add_inputs(
               PARAMS["annotations_interface_genomic_context_bed"]),
           ".contextstats.tsv.gz")
def buildContextStats(infiles, outfile):
    '''build mapping context stats.

    Examines the genomic context to where reads align.

    A read is assigned to the genomic context that it overlaps by at
    least 50%. Thus some reads that map across several non-overlapping
    contexts might be dropped.

    '''
    PipelineWindows.summarizeTagsWithinContext(
        infiles[0], infiles[1], outfile)


@jobs_limit(PARAMS.get("jobs_limit_db", 1), "db")
@follows(loadBAMStats)
@merge(buildContextStats, "context_stats.load")
def loadContextStats(infiles, outfile):
    """
    load context mapping statistics."""
    PipelineWindows.loadSummarizedContextStats(infiles, outfile)

###################################################################
###################################################################
###################################################################
# QC specific to spliced mapping
###################################################################
###################################################################
###################################################################


@active_if(SPLICED_MAPPING)
@transform(MAPPINGTARGETS,
           suffix(".bam"),
           add_inputs(buildCodingExons),
           ".exon.validation.tsv.gz")
def buildExonValidation(infiles, outfile):
    '''count number of reads mapped, duplicates, etc.
    '''

    infile, exons = infiles
    statement = '''cat %(infile)s
    | python %(scriptsdir)s/bam_vs_gtf.py
         --exons-file=%(exons)s
         --force-output
         --log=%(outfile)s.log
         --output-filename-pattern="%(outfile)s.%%s.gz"
    | gzip
    > %(outfile)s
    '''

    P.run()


@jobs_limit(PARAMS.get("jobs_limit_db", 1), "db")
@active_if(SPLICED_MAPPING)
@merge(buildExonValidation, "exon_validation.load")
def loadExonValidation(infiles, outfile):
    '''merge alignment stats into single tables.'''
    suffix = ".exon.validation.tsv.gz"
    P.mergeAndLoad(infiles, outfile, suffix=suffix)
    for infile in infiles:
        track = P.snip(infile, suffix)
        o = "%s_overrun.load" % track
        P.load(infile + ".overrun.gz", o)


@active_if(SPLICED_MAPPING)
@transform(MAPPINGTARGETS,
           regex("(.+).bam"),
           add_inputs(buildCodingGeneSet),
           r"\1.transcript_counts.tsv.gz")
def buildTranscriptLevelReadCounts(infiles, outfile):
    '''count reads falling into transcripts of protein coding
       gene models.

    .. note::
       In paired-end data sets each mate will be counted. Thus
       the actual read counts are approximately twice the fragment
       counts.

    '''
    infile, geneset = infiles

    job_memory = "8G"

    statement = '''
    zcat %(geneset)s
    | python %%(scriptsdir)s/gtf2table.py
    --reporter=transcripts
    --bam-file=%(infile)s
    --counter=length
    --column-prefix="exons_"
    --counter=read-counts
    --column-prefix=""
    --counter=read-coverage
    --column-prefix=coverage_
    -v 0
    | gzip
    > %(outfile)s
    ''' % locals()

    P.run()


@jobs_limit(PARAMS.get("jobs_limit_db", 1), "db")
@active_if(SPLICED_MAPPING)
@transform(buildTranscriptLevelReadCounts,
           suffix(".tsv.gz"),
           ".load")
def loadTranscriptLevelReadCounts(infile, outfile):
    P.load(infile, outfile,
           options="--add-index=transcript_id --allow-empty-file")


@active_if(SPLICED_MAPPING)
@transform(MAPPINGTARGETS,
           suffix(".bam"),
           add_inputs(buildIntronGeneModels),
           ".intron_counts.tsv.gz")
def buildIntronLevelReadCounts(infiles, outfile):
    '''compute coverage of exons with reads.
    '''

    infile, exons = infiles

    job_memory = "4G"

    if "transcriptome.dir" in infile:
        P.touch(outfile)
        return

    statement = '''
    zcat %(exons)s
    | python %(scriptsdir)s/gtf2table.py
          --reporter=genes
          --bam-file=%(infile)s
          --counter=length
          --column-prefix="introns_"
          --counter=read-counts
          --column-prefix=""
          --counter=read-coverage
          --column-prefix=coverage_
    | gzip
    > %(outfile)s
    '''

    P.run()


@jobs_limit(PARAMS.get("jobs_limit_db", 1), "db")
@active_if(SPLICED_MAPPING)
@transform(buildIntronLevelReadCounts,
           suffix(".tsv.gz"),
           ".load")
def loadIntronLevelReadCounts(infile, outfile):
    P.load(infile, outfile, options="--add-index=gene_id --allow-empty-file")


@merge((countReads, mergeReadCounts), "reads_summary.load")
def loadReadCounts(infiles, outfile):
    '''load read counts into database.'''

    outf = P.getTempFile(".")
    outf.write("track\ttotal_reads\n")
    for infile in infiles:
        track = P.snip(infile, ".nreads")
        lines = IOTools.openFile(infile).readlines()
        nreads = int(lines[0][:-1].split("\t")[1])
        outf.write("%s\t%i\n" % (track, nreads))
    outf.close()

    P.load(outf.name, outfile)

    os.unlink(outf.name)


@active_if(SPLICED_MAPPING)
@transform(MAPPINGTARGETS,
           suffix(".bam"),
           add_inputs(buildCodingExons),
           ".transcriptprofile.gz")
def buildTranscriptProfiles(infiles, outfile):
    '''build gene coverage profiles.'''

    bamfile, gtffile = infiles

    job_memory = "8G"

    statement = '''python %(scriptsdir)s/bam2geneprofile.py
    --output-filename-pattern="%(outfile)s.%%s"
    --force-output
    --reporter=transcript
    --use-base-accuracy
    --method=geneprofileabsolutedistancefromthreeprimeend
    --normalize-profile=all
    %(bamfile)s %(gtffile)s
    | gzip
    > %(outfile)s
    '''

    P.run()


###################################################################
###################################################################
# various export functions
###################################################################
@transform(MAPPINGTARGETS,
           regex(".bam"),
           ".bw")
def buildBigWig(infile, outfile):
    '''build wiggle files from bam files.'''

    if SPLICED_MAPPING:
        # use bedtools for RNASEQ data

        # scale by Mio reads mapped
        reads_mapped = BamTools.getNumberOfAlignments(infile)
        scale = 1000000.0 / float(reads_mapped)
        tmpfile = P.getTempFilename()
        contig_sizes = PARAMS["annotations_interface_contigs"]
        job_memory = "3G"
        statement = '''bedtools genomecov
        -ibam %(infile)s
        -g %(contig_sizes)s
        -bg
        -split
        -scale %(scale)f
        > %(tmpfile)s;
        checkpoint;
        bedGraphToBigWig %(tmpfile)s %(contig_sizes)s %(outfile)s;
        checkpoint;
        rm -f %(tmpfile)s
        '''
    else:
        # wigToBigWig observed to use 16G
        job_memory = "16G"
        statement = '''python %(scriptsdir)s/bam2wiggle.py
        --output-format=bigwig
        %(bigwig_options)s
        %(infile)s
        %(outfile)s
        > %(outfile)s.log'''
    P.run()


@merge(buildBigWig,
       "bigwig_stats.load")
def loadBigWigStats(infiles, outfile):
    '''load bigwig summary for all wiggle files.'''

    data = " ".join(
        ['<( bigWigInfo %s | perl -p -e "s/:/\\t/; s/ //g; s/,//g")' %
         x for x in infiles])
    headers = ",".join([P.snip(os.path.basename(x), ".bw")
                        for x in infiles])

    load_statement = P.build_load_statement(
        P.toTable(outfile),
        options="--add-index=track")

    statement = '''python %(scriptsdir)s/combine_tables.py
    --header-names=%(headers)s
    --skip-titles
    --missing-value=0
    --ignore-empty
    %(data)s
    | perl -p -e "s/bin/track/"
    | python %(scriptsdir)s/table2table.py --transpose
    | %(load_statement)s
    > %(outfile)s
    '''

    P.run()


@transform(MAPPINGTARGETS,
           regex(".bam"),
           ".bed.gz")
def buildBed(infile, outfile):
    '''build bed files from bam files.'''

    statement = '''
    cat %(infile)s
    | python %(scriptsdir)s/bam2bed.py
          %(bed_options)s
          --log=%(outfile)s.log
          -
    | sort -k1,1 -k2,2n
    | bgzip
    > %(outfile)s;
    tabix -p bed %(outfile)s
    '''
    P.run()


@merge(buildBigWig, "igv_sample_information.tsv")
def buildIGVSampleInformation(infiles, outfile):
    '''build a file with IGV sample information.'''

    outf = IOTools.openFile(outfile, "w")
    first = True
    for fn in infiles:
        fn = os.path.basename(fn)
        parts = fn.split("-")
        if first:
            outf.write("sample\t%s\n" % "\t".join(
                ["%i" % x for x in range(len(parts))]))
            first = False
        outf.write("%s\t%s\n" % (fn, "\t".join(parts)))

    outf.close()


@follows(loadReadCounts,
         loadPicardStats,
         loadBAMStats,
         loadContextStats)
def general_qc():
    pass


@active_if(SPLICED_MAPPING)
@follows(loadExonValidation,
         loadGeneInformation,
         loadTranscriptLevelReadCounts,
         loadIntronLevelReadCounts,
         buildTranscriptProfiles)
def spliced_qc():
    pass


@follows(general_qc, spliced_qc)
def qc():
    pass


@follows(loadPicardDuplicationStats)
def duplication():
    pass


@follows(buildBigWig, loadBigWigStats)
def wig():
    pass


@merge((loadBAMStats, loadPicardStats, loadContextStats), "view_mapping.load")
def createViewMapping(infile, outfile):
    '''create view in database for alignment stats.

    This view aggregates all information on a per-track basis.

    The table is built from the following tracks:

       context_stats
       bam_stats

    '''

    dbh = connect()

    tablename = P.toTable(outfile)
    view_type = "TABLE"

    tables = (("bam_stats", "track", ),
              ("context_stats", "track", ))

    # do not use: ("picard_stats_alignment_summary_metrics", "track"),)
    # as there are multiple rows per track for paired-ended data.

    P.createView(dbh, tables, tablename, outfile, view_type)


@follows(createViewMapping)
def views():
    pass


@follows(mapping, qc, views, duplication)
def full():
    pass


@follows(buildCodingGeneSet)
def test():
    pass


@follows(mapping)
def map_only():
    pass


@follows(mkdir("report"), mkdir(PARAMS.get("exportdir"), "export"))
def build_report():
    '''build report from scratch.'''
    P.run_report(clean=True)


@follows(mkdir("report"))
def update_report():
    '''update report.'''
    P.run_report(clean=False)


@follows(mkdir("%s/bamfiles" % PARAMS["web_dir"]),
         mkdir("%s/bigwigfiles" % PARAMS["web_dir"]),
         )
def publish():
    '''publish files.'''

    # directory, files
    export_files = {
        "bamfiles": glob.glob("*/*.bam") + glob.glob("*/*.bam.bai"),
        "bigwigfiles": glob.glob("*/*.bw"),
    }

    # publish web pages
    E.info("publishing report")
    P.publish_report(export_files=export_files)

    E.info("publishing UCSC data hub")
    P.publish_tracks(export_files)


if __name__ == "__main__":
    sys.exit(P.main(sys.argv))
