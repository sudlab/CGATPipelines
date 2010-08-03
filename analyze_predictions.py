################################################################################
#
#   MRC FGU Computational Genomics Group
#
#   $Id$
#
#   Copyright (C) 2009 Andreas Heger
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
#################################################################################
'''
analyze_predictions.py - 
======================================================

:Author: Andreas Heger
:Release: $Id$
:Date: |today|
:Tags: Python

Purpose
-------

.. todo::
   
   describe purpose of the script.

Usage
-----

Example::

   python analyze_predictions.py --help

Type::

   python analyze_predictions.py --help

for command line help.

Documentation
-------------

Code
----

'''
import os, sys, string, re, getopt, time, sets, optparse, math, tempfile

import pgdb, csv
""" program $Id: analyze_predictions.py 2781 2009-09-10 11:33:14Z andreas $

analyse a prediction list


"""
import Experiment

if __name__ == "__main__":

    parser = optparse.OptionParser( version = "%prog version: $Id: analyze_predictions.py 2781 2009-09-10 11:33:14Z andreas $")

    parser.add_option( "-s", "--species-regex", dest="species_regex", type="string" ,
                       help="regular expression to extract species from identifier.")

    parser.add_option( "-g", "--gene-regex", dest="gene_regex", type="string" ,
                       help="regular expression to extract gene from identifier.")

    parser.add_option( "-m", "--methods", dest="methods", type="string" ,
                       help="methods to use [query|].")

    parser.set_defaults(
        species_regex ="^([^|]+)\|",
        gene_regex = "^[^|]+\|[^|]+\|([^|]+)\|",
        methods = "query",
        tablename_predictions = "predictions",
        separator = "|" )

    (options, args) = Experiment.Start( parser, add_psql_options = True, add_csv_options = True )
    options.methods = options.methods.split(",")
    dbhandle = pgdb.connect( options.psql_connection )

    fields = []

    for method in options.methods:
        if method == "query":
            fields += [ "query", "lquery" ]
        elif method == "nexons":
            fields.append( "nexons" )
        else:
            raise "unknown method %s" % method

    outfile = sys.stdout
    writer = csv.DictWriter( outfile,
                             fields,
                             dialect=options.csv_dialect,
                             lineterminator = options.csv_lineterminator,
                             extrasaction = 'ignore' )

    first = True
    for line in sys.stdin:
        if line[0] == "#": continue

        data = line[:-1].split("\t")

        if first:
            outfile.write( "\t".join(data + fields) + "\n" )
            first = False
            continue

        schema, prediction_id, gene_id, quality = data[0].split( options.separator )

        outfile.write( line[:-1] )
        
        for method in options.methods:

            if method == "query":
                statement = "SELECT query_token, query_length FROM %s.%s WHERE prediction_id = '%s'" % (schema,
                                                                                                        options.tablename_predictions,
                                                                                                        prediction_id )
            elif method == "nexons":
                statement = "SELECT nintrons+1 FROM %s.%s WHERE prediction_id = '%s'" % (schema,
                                                                                         options.tablename_predictions,
                                                                                         prediction_id )


            cc = dbhandle.cursor()
            cc.execute(statement)
            rr = cc.fetchone()
            cc.close()

            for x in rr:
                outfile.write( "\t%s" % str(x) )
                
        outfile.write("\n")
            
    Experiment.Stop()
