from CGATReport.Tracker import *
import sqlite3
import collections


class ContributingReads(TrackerSQL):

    '''
    returns the proportion of reads 
    that contribute to the relative abundance
    estimations
    '''
    pattern = "(.*)_readmap"

    def __call__(self, track, slice=None):

        if len(track.split("_")) == 4:
            dtrack = track.split("_")
            dtrack = dtrack[0] + "-" + dtrack[1] + \
                "_" + dtrack[2] + "-" + dtrack[3]
        else:
            dtrack = track.replace("_", "-")
        total_stmt = """SELECT total_reads FROM reads_summary WHERE track == '%s'""" % dtrack
        dbh = sqlite3.connect("csvdb")
        cc = dbh.cursor()
        total = cc.execute(total_stmt).fetchone()[0]
        # returns the number at the phylum level
        statement = """SELECT count(*) FROM %s_readmap""" % track
        return float(self.execute(statement).fetchone()[0]) / total


class RelativeAbundance(TrackerSQL):

    '''
    summarises the relative abundance at
    different taxonomic levels - results
    from metaphlan
    '''
    pattern = "(.*)_relab"

    def __call__(self, track, slice=None):
        '''
        only displays those above 1% relative abundance
        '''
        result = {"phylum": {}, "class": {}, "order": {},
                  "family": {}, "genus": {}, "species": {}}
        for taxon in list(result.keys()):
            statement = """SELECT taxon, rel_abundance FROM %s_relab
                           WHERE taxon_level == '%s' AND rel_abundance > 1""" % (track, taxon)
            for tax, rel in self.execute(statement).fetchall():
                result[taxon][tax] = rel
        return result


class TotalSpecies(TrackerSQL):

    '''
    Summarises the total number of groups at
    each level that were detected in the samples
    '''
    pattern = "(.*)_relab"

    def __call__(self, track, slice=None):
        '''
        only displays those above 1% relative abundance
        '''
        taxon_levels = [
            "phylum", "class", "order", "family", "genus", "species"]
        result = collections.defaultdict(int)
        for taxon in taxon_levels:
            statement = """SELECT taxon FROM %s_relab
                           WHERE taxon_level == '%s'""" % (track, taxon)
            for tax in self.execute(statement).fetchall():
                result[taxon] += 1
        return result
